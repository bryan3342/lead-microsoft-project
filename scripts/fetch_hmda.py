"""HMDA mortgage lending (FFIEC/CFPB Data Browser), sample counties, 2021-latest.

Raw: data/raw/hmda/<date>/hmda_<year>.csv.gz (loan-level, as published) + reporter panels
Processed:
  hmda_loans        loan-level records WITHOUT race, ethnicity, sex or age fields (SOW fair-lending guardrail)
  hmda_tract_year   per tract and year: applications, originations, denials, denial rate, high-cost share
  hmda_lenders      LEI -> Fed RSSD crosswalk (joins HMDA lenders to FDIC banks via institutions.fed_rssd)
"""

import gzip
import io
import re
import shutil
import sys
import zipfile

import pandas as pd

from common import PROCESSED, START_YEAR, get, raw_dir, sample_counties, write_processed, write_provenance

API = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv"
PANEL = "https://files.ffiec.cfpb.gov/static-data/snapshot/{year}/{year}_public_panel_csv.zip"
LATEST_YEAR = 2025

# Protected-class fields are dropped at ingest; they are never stored in processed tables.
PROTECTED = re.compile(r"(ethnicity|race|sex|_age|minority)", re.I)

ACTION = {
    1: "originated",
    2: "approved_not_accepted",
    3: "denied",
    4: "withdrawn",
    5: "incomplete",
    6: "purchased",
    7: "preapproval_denied",
    8: "preapproval_approved_not_accepted",
}


def download_year(year, counties):
    params = {"years": year, "counties": ",".join(counties)}
    resp = get(API, params=params, timeout=300)
    # The API answers with a pointer to a pre-built file rather than the data itself.
    match = re.search(r'href="([^"]+\.csv)"', resp.text)
    url = match.group(1) if match else resp.url
    out = raw_dir("hmda") / f"hmda_{year}.csv.gz"
    with get(url, stream=True, timeout=600) as src, gzip.open(out, "wb") as dst:
        # The server sometimes gzips the response itself; decode it so the file isn't compressed twice.
        src.raw.decode_content = True
        shutil.copyfileobj(src.raw, dst)
    df = pd.read_csv(out, dtype=str, low_memory=False)
    write_provenance(out, url, {"api": API, **params}, rows=len(df))
    print(f"  {year}: {len(df):,} records")
    return df


def lenders():
    frames = []
    for year in range(START_YEAR, LATEST_YEAR + 1):
        url = PANEL.format(year=year)
        try:
            content = get(url, timeout=120).content
        except Exception:
            print(f"  panel {year}: not published")
            continue
        out = raw_dir("hmda_panels", shared=True) / f"panel_{year}.zip"
        out.write_bytes(content)
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            df = pd.read_csv(zf.open(zf.namelist()[0]), dtype=str)
        write_provenance(out, url, rows=len(df))
        frames.append(df)
        print(f"  panel {year}: {len(df):,} lenders")
    panel = pd.concat(frames).sort_values("activity_year").drop_duplicates("lei", keep="last")
    out = panel[["lei", "activity_year", "respondent_rssd", "respondent_name", "respondent_state", "agency_code", "assets"]].rename(
        columns={"activity_year": "panel_year", "respondent_rssd": "fed_rssd"}
    )
    write_processed(out, "hmda_lenders")


PURPOSE_GROUP = {1: "home_purchase", 31: "refinance", 32: "refinance", 2: "other", 4: "other", 5: "other"}


def to_2020_tracts(loans):
    """HMDA 2021 uses 2010 tract boundaries; split those loans across 2020 tracts by land share.
    Returns (tract_geoid, weight) per loan row: weight 1 for 2022+, fractional for converted 2021 rows."""
    xwalk = pd.read_parquet(PROCESSED / "tract_2010_2020.parquet")
    current = loans[loans["activity_year"] >= 2022].assign(tract_geoid=lambda d: d["census_tract"], weight=1.0)
    old = loans[loans["activity_year"] < 2022].merge(xwalk, left_on="census_tract", right_on="tract_2010", how="left")
    unmatched = old["tract_2020"].isna()
    old["tract_geoid"] = old["tract_2020"].where(~unmatched, old["census_tract"])
    old["weight"] = old["share_of_2010_tract"].where(~unmatched, 1.0)
    return pd.concat([current, old.drop(columns=["tract_2010", "tract_2020", "share_of_2010_tract"])], ignore_index=True)


def build_tract_year(loans):
    """Tract x year x loan-purpose lending signals. Applications exclude purchased loans (not consumer decisions).
    Home purchase is the cleanest access signal: refinance volume swings with interest rates (2021 refi boom)."""
    apps = loans[loans["action_taken"].isin([1, 2, 3, 4, 5])].copy()
    apps["activity_year"] = apps["activity_year"].astype(int)
    apps["purpose"] = apps["loan_purpose"].map(PURPOSE_GROUP).fillna("other")
    apps = to_2020_tracts(apps)
    w = apps["weight"]
    apps["applications"] = w
    apps["originations"] = w * (apps["action_taken"] == 1)
    apps["denials"] = w * (apps["action_taken"] == 3)
    # High-cost: first-lien originations priced 1.5+ points above the average prime offer rate.
    apps["high_cost_originations"] = w * ((apps["action_taken"] == 1) & (apps["lien_status"] == 1) & (apps["rate_spread"] >= 1.5))
    apps["originated_amount_000"] = w * (apps["action_taken"] == 1) * apps["loan_amount"] / 1000
    apps["converted_from_2010"] = w * (apps["activity_year"] < 2022)
    measures = ["applications", "originations", "denials", "high_cost_originations", "originated_amount_000", "converted_from_2010"]

    by_purpose = apps.groupby(["tract_geoid", "activity_year", "purpose"])[measures].sum().reset_index()
    total = apps.groupby(["tract_geoid", "activity_year"])[measures].sum().reset_index().assign(purpose="all")
    tract = pd.concat([total, by_purpose], ignore_index=True).rename(columns={"activity_year": "year", "purpose": "loan_purpose_group"})

    # Owner-occupied homes per tract come from HMDA's own tract fields (2020 boundaries, 2022+ filings).
    owner_units = loans[loans["activity_year"].astype(int) >= 2022].groupby("census_tract")["tract_owner_occupied_units"].max()
    tract["owner_occupied_units"] = tract["tract_geoid"].map(owner_units)
    tract["denial_rate"] = tract["denials"] / (tract["originations"] + tract["denials"]).where(lambda s: s > 0)
    tract["high_cost_share"] = tract["high_cost_originations"] / tract["originations"].where(lambda s: s > 0)
    tract["originations_per_1k_owner_units"] = 1000 * tract["originations"] / tract["owner_occupied_units"].where(lambda s: s > 0)
    tract["share_converted_from_2010_tracts"] = tract["converted_from_2010"] / tract["applications"].where(lambda s: s > 0)
    tract = tract.drop(columns="converted_from_2010")
    counts = ["applications", "originations", "denials", "high_cost_originations"]
    tract[counts] = tract[counts].round(2)
    return tract


def main():
    if "--rebuild" in sys.argv:
        # Rebuild the tract table from the saved loan-level data without downloading again.
        loans = pd.read_parquet(PROCESSED / "hmda_loans.parquet")
        loans["activity_year"] = loans["activity_year"].astype(int)
        write_processed(build_tract_year(loans), "hmda_tract_year")
        return

    counties = sample_counties()
    loans = []
    for year in range(START_YEAR, LATEST_YEAR + 1):
        df = download_year(year, counties)
        loans.append(df[[c for c in df.columns if not PROTECTED.search(c)]])
    loans = pd.concat(loans, ignore_index=True)

    numeric = ["action_taken", "loan_amount", "income", "rate_spread", "interest_rate", "hoepa_status",
               "tract_population", "tract_owner_occupied_units", "tract_to_msa_income_percentage",
               "ffiec_msa_md_median_family_income", "property_value", "loan_purpose", "lien_status"]
    for col in numeric:
        if col in loans:
            loans[col] = pd.to_numeric(loans[col], errors="coerce")
    loans["activity_year"] = loans["activity_year"].astype(int)
    loans["action"] = loans["action_taken"].map(ACTION)
    write_processed(loans, "hmda_loans")

    write_processed(build_tract_year(loans), "hmda_tract_year")
    lenders()


if __name__ == "__main__":
    main()
