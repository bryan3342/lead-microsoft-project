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
import zipfile

import pandas as pd

from common import START_YEAR, get, raw_dir, sample_counties, write_processed, write_provenance

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
        out = raw_dir("hmda") / f"panel_{year}.zip"
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


def main():
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
    loans["action"] = loans["action_taken"].map(ACTION)
    write_processed(loans, "hmda_loans")

    # Tract-level lending signals (applications exclude purchased loans, which are not consumer decisions).
    apps = loans[loans["action_taken"].isin([1, 2, 3, 4, 5])]
    g = apps.groupby(["census_tract", "activity_year"])
    tract = pd.DataFrame(
        {
            "applications": g.size(),
            "originations": g["action_taken"].apply(lambda s: (s == 1).sum()),
            "denials": g["action_taken"].apply(lambda s: (s == 3).sum()),
            "median_loan_amount_000": g.apply(lambda d: d.loc[d.action_taken == 1, "loan_amount"].median() / 1000),
            # High-cost: first-lien originations priced 1.5+ points above the average prime offer rate.
            "high_cost_originations": g.apply(
                lambda d: ((d.action_taken == 1) & (d.lien_status == 1) & (d.rate_spread >= 1.5)).sum()
            ),
            "owner_occupied_units": g["tract_owner_occupied_units"].max(),
            "tract_to_msa_income_pct": g["tract_to_msa_income_percentage"].max(),
        }
    ).reset_index()
    tract = tract.rename(columns={"census_tract": "tract_geoid", "activity_year": "year"})
    tract["denial_rate"] = tract["denials"] / (tract["originations"] + tract["denials"]).where(lambda s: s > 0)
    tract["high_cost_share"] = tract["high_cost_originations"] / tract["originations"].where(lambda s: s > 0)
    tract["originations_per_1k_owner_units"] = 1000 * tract["originations"] / tract["owner_occupied_units"].where(
        lambda s: s > 0
    )
    write_processed(tract, "hmda_tract_year")

    lenders()


if __name__ == "__main__":
    main()
