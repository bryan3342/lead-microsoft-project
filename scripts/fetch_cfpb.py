"""CFPB Consumer Complaint Database, sample-area ZIP codes, 2021-latest.

Uses the daily bulk export rather than the search API: the API's search window caps at 10,000 hits per query,
which the sample states exceed.

Raw: data/raw/cfpb/<date>/complaints.csv.zip (as published)
Processed:
  complaints            complaint-level records in sample ZIPs (narrative text excluded)
  complaints_zip_year   counts per ZIP, year and product
"""

import shutil
import zipfile

import pandas as pd

from common import PROCESSED, SAMPLE_STATES, START_YEAR, get, raw_dir, sample_counties, write_processed, write_provenance

BULK_URL = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
COLUMNS = {
    "Complaint ID": "complaint_id",
    "Date received": "date_received",
    "Product": "product",
    "Sub-product": "sub_product",
    "Issue": "issue",
    "Sub-issue": "sub_issue",
    "Company": "company",
    "State": "state",
    "ZIP code": "zip",
    "Tags": "tags",
    "Submitted via": "submitted_via",
    "Company response to consumer": "company_response",
    "Timely response?": "timely_response",
}


# Product groups. Credit-reporting complaints are ~80% of volume (much of it mass-filed through credit-repair
# services), so raw totals are a poor trust signal; banking_access is the closest proxy for distrust of accounts.
PRODUCT_GROUPS = {
    "banking_access": ["Checking or savings account", "Bank account or service", "Money transfer",
                       "Money transfer, virtual currency, or money service", "Prepaid card"],
    "consumer_credit": ["Credit card", "Credit card or prepaid card", "Payday loan", "Payday loan, title loan, or personal loan",
                        "Payday loan, title loan, personal loan, or advance loan", "Consumer Loan",
                        "Vehicle loan or lease", "Student loan", "Mortgage"],
    "debt_collection": ["Debt collection", "Debt or credit management"],
    "credit_reporting": ["Credit reporting or other personal consumer reports",
                         "Credit reporting, credit repair services, or other personal consumer reports",
                         "Credit reporting"],
}
PRODUCT_TO_GROUP = {p: g for g, products in PRODUCT_GROUPS.items() for p in products}


def sample_zips():
    """ZCTAs that overlap any census tract in the sample counties."""
    xwalk = pd.read_csv(PROCESSED / "zcta_tract.csv", dtype={"zcta": str, "tract_geoid": str})
    counties = set(sample_counties())
    return set(xwalk.loc[xwalk["tract_geoid"].str[:5].isin(counties), "zcta"])


def main():
    out = raw_dir("cfpb") / "complaints.csv.zip"
    if not out.exists():
        with get(BULK_URL, stream=True, timeout=900) as src, open(out, "wb") as dst:
            shutil.copyfileobj(src.raw, dst)
    print(f"  bulk file: {out.stat().st_size / 1e6:,.0f} MB")

    zips = sample_zips()
    states = set(SAMPLE_STATES.values())
    kept, total = [], 0
    with zipfile.ZipFile(out) as zf:
        with zf.open(zf.namelist()[0]) as fh:
            for chunk in pd.read_csv(fh, usecols=list(COLUMNS), dtype=str, chunksize=500_000):
                total += len(chunk)
                chunk = chunk.rename(columns=COLUMNS)
                chunk = chunk[chunk["state"].isin(states) & (chunk["date_received"] >= f"{START_YEAR}-01-01")]
                kept.append(chunk)
    write_provenance(out, BULK_URL, rows=total)

    df = pd.concat(kept, ignore_index=True)
    in_states = len(df)
    df["zip"] = df["zip"].str[:5]
    masked = df["zip"].str.contains("X", na=True)
    df = df[~masked & df["zip"].isin(zips)].copy()
    df["year"] = df["date_received"].str[:4].astype(int)
    df["product_group"] = df["product"].map(PRODUCT_TO_GROUP).fillna("other")
    print(
        f"  {total:,} complaints nationally; {in_states:,} in sample states since {START_YEAR}; "
        f"{masked.sum():,} with masked/missing ZIP dropped; {len(df):,} in sample ZIPs"
    )
    write_processed(df, "complaints")

    by_zip = df.groupby(["zip", "year", "product_group", "product"]).size().rename("complaints").reset_index()
    write_processed(by_zip, "complaints_zip_year")


if __name__ == "__main__":
    main()
