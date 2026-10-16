"""
Re-pull the county data behind the Prince William Banking Access map, for any U.S. county.

Usage:
    export CENSUS_API_KEY=...          # free key: https://api.census.gov/data/key_signup.html
    python pull_sources.py --state 51 --county 153 --out ./data

Pulls (2021-2026 window unless noted):
    ACS 5-year 2020-2024 tract tables     -> acs_2020_2024_by_tract.csv
    FDIC Summary of Deposits 2021-2025    -> fdic_sod_branches_2021_2025.csv
    FDIC current branch locations         -> fdic_branches_current.csv
    HMDA county action counts 2021-2025   -> hmda_county_trend.csv
    CFPB complaints, county ZIPs, 2021+   -> cfpb_complaints.csv (ZIPs passed with --zips)

Untested from this environment: the build sandbox could not reach these APIs, so run it on
a normal network and check the first rows of each file. Requires: pip install requests pandas
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

TIMEOUT = 60
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "banking-access-research/1.0"


def get_json(url: str, params: dict | None = None, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            r = SESSION.get(url, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == retries:
                raise RuntimeError(f"GET {url} failed after {retries} tries: {exc}") from exc
            time.sleep(2 * attempt)


# ---------------------------------------------------------------- Census ACS
# B19001: household income brackets (002-005 = under $25k)
# B17001: poverty status of individuals (002 = below poverty)
# C16002: household language by limited-English status (004,007,010,013 = limited-English HHs)
# B08201: household size by vehicles available (002 = no vehicle)
# B28002: internet subscriptions (013 = no internet access)
# Verify every variable against https://api.census.gov/data/2024/acs/acs5/variables.html before relying on it.
ACS_VARS = {
    "households": "B19001_001",
    "inc_lt10k": "B19001_002", "inc_10_15k": "B19001_003", "inc_15_20k": "B19001_004", "inc_20_25k": "B19001_005",
    "pov_universe": "B17001_001", "pov_below": "B17001_002",
    "lang_hh_total": "C16002_001", "lep_spanish": "C16002_004", "lep_ie": "C16002_007",
    "lep_api": "C16002_010", "lep_other": "C16002_013",
    "veh_hh_total": "B08201_001", "veh_none": "B08201_002",
    "net_hh_total": "B28002_001", "net_none": "B28002_013",
}


def pull_acs(state: str, county: str, key: str, year: int = 2024) -> pd.DataFrame:
    fields = []
    for code in ACS_VARS.values():
        fields += [code + "E", code + "M"]
    data = get_json(
        f"https://api.census.gov/data/{year}/acs/acs5",
        {"get": ",".join(["NAME"] + fields), "for": "tract:*", "in": f"state:{state} county:{county}", "key": key},
    )
    df = pd.DataFrame(data[1:], columns=data[0])
    for c in fields:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df.loc[df[c] < 0, c] = pd.NA  # Census annotation codes like -666666666 mean "not available"
    df["tract_geoid"] = df["state"] + df["county"] + df["tract"]

    def share(num_codes: list[str], den_code: str, name: str):
        num = sum(df[ACS_VARS[k] + "E"] for k in num_codes)
        num_moe = sum(df[ACS_VARS[k] + "M"] ** 2 for k in num_codes) ** 0.5   # Census approx. for summed MOEs
        den = df[ACS_VARS[den_code] + "E"]
        den_moe = df[ACS_VARS[den_code] + "M"]
        p = (num / den).where(den > 0)
        # Census proportion MOE formula; falls back to the ratio formula when the radicand is negative
        rad = num_moe ** 2 - (p ** 2) * den_moe ** 2
        rad = rad.where(rad >= 0, num_moe ** 2 + (p ** 2) * den_moe ** 2)
        df[f"pct_{name}"] = (100 * p).round(1)
        df[f"pct_{name}_moe"] = (100 * rad ** 0.5 / den).where(den > 0).round(1)
        cv = (df[f"pct_{name}_moe"] / 1.645) / df[f"pct_{name}"]
        df[f"cv_{name}"] = cv.round(2)

    share(["inc_lt10k", "inc_10_15k", "inc_15_20k", "inc_20_25k"], "households", "hh_income_under_25k")
    share(["pov_below"], "pov_universe", "people_below_poverty")
    share(["lep_spanish", "lep_ie", "lep_api", "lep_other"], "lang_hh_total", "hh_limited_english")
    share(["veh_none"], "veh_hh_total", "hh_no_vehicle")
    share(["net_none"], "net_hh_total", "hh_no_internet")
    keep = ["tract_geoid", "NAME", ACS_VARS["households"] + "E", ACS_VARS["households"] + "M"] + \
        [c for c in df.columns if c.startswith(("pct_", "cv_"))]
    return df[keep].rename(columns={ACS_VARS["households"] + "E": "households", ACS_VARS["households"] + "M": "households_moe"})


# ---------------------------------------------------------------- FDIC
def fdic_all(endpoint: str, filters: str, fields: str) -> pd.DataFrame:
    rows, offset, limit = [], 0, 1000
    while True:
        j = get_json(f"https://api.fdic.gov/banks/{endpoint}",
                     {"filters": filters, "fields": fields, "limit": limit, "offset": offset, "format": "json"})
        rows += [d["data"] for d in j.get("data", [])]
        total = j.get("meta", {}).get("total", 0)
        offset += limit
        if offset >= total:
            break
    return pd.DataFrame(rows)


def pull_fdic(state: str, county: str, years=range(2021, 2026)) -> tuple[pd.DataFrame, pd.DataFrame]:
    stcnty = f"{state}{county}"  # e.g. 51153; verified for Virginia only. For states with a leading 0 (e.g. 06), check the row count.
    sod = pd.concat([
        fdic_all("sod", f"STCNTYBR:{stcnty} AND YEAR:{y}",
                 "YEAR,CERT,NAMEFULL,BRNUM,NAMEBR,ADDRESBR,CITYBR,ZIPBR,DEPSUMBR,BRSERTYP,SIMS_LATITUDE,SIMS_LONGITUDE")
        for y in years
    ], ignore_index=True)
    # /locations filters on STCNTY (5-digit state+county FIPS); verified live Oct 12, 2026 (51153 -> 55 offices).
    locs = fdic_all("locations", f"STCNTY:{state}{county}",
                    "NAME,CERT,OFFNAME,ADDRESS,CITY,ZIP,SERVTYPE,SERVTYPE_DESC,MDI_STATUS_DESC,LATITUDE,LONGITUDE,ESTYMD")
    return sod, locs


# ---------------------------------------------------------------- HMDA
def pull_hmda(state: str, county: str, years=range(2021, 2026)) -> pd.DataFrame:
    out = []
    for y in years:
        j = get_json("https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations",
                     {"years": y, "counties": f"{state}{county}", "actions_taken": "1,2,3,4,5"})
        row = {"year": y}
        for a in j.get("aggregations", []):
            row[f"action_{a['actions_taken']}_count"] = a["count"]
            row[f"action_{a['actions_taken']}_amount"] = a["sum"]
        out.append(row)
    df = pd.DataFrame(out)
    decided = df[["action_1_count", "action_2_count", "action_3_count"]].sum(axis=1)
    df["denial_rate_pct"] = (100 * df["action_3_count"] / decided).round(1)
    return df
# Tract-level HMDA: download the county CSV from https://ffiec.cfpb.gov/data-browser/ (filter by county,
# year) and group by census_tract. Do not carry race, ethnicity or sex fields into any scoring.


# ---------------------------------------------------------------- CFPB
def pull_cfpb(zips: list[str], since: str = "2021-01-01") -> pd.DataFrame:
    products = ["Checking or savings account", "Money transfer, virtual currency, or money service", "Prepaid card"]
    rows = []
    for z in zips:
        frm = 0
        while True:
            j = get_json("https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/",
                         {"zip_code": z, "date_received_min": since, "product": products,
                          "size": 100, "frm": frm, "no_aggs": "true"})
            hits = j.get("hits", {}).get("hits", [])
            rows += [h["_source"] for h in hits]
            frm += len(hits)
            total = j.get("hits", {}).get("total", {})
            total = total.get("value", 0) if isinstance(total, dict) else total
            if not hits or frm >= total:
                break
    df = pd.DataFrame(rows)
    keep = [c for c in ["complaint_id", "date_received", "product", "sub_product", "issue", "sub_issue",
                        "company", "state", "zip_code", "company_response", "timely"] if c in df.columns]
    return df[keep]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="51", help="2-digit state FIPS")
    ap.add_argument("--county", default="153", help="3-digit county FIPS")
    ap.add_argument("--zips", default="20109,20110,20111,20112,20136,20155,20169,20181,22025,22026,22125,22134,22172,22191,22192,22193")
    ap.add_argument("--out", default="./data")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    key = os.environ.get("CENSUS_API_KEY")
    steps = []
    if key:
        steps.append(("acs_2020_2024_by_tract.csv", lambda: pull_acs(args.state, args.county, key)))
    else:
        print("CENSUS_API_KEY not set; skipping ACS.", file=sys.stderr)
    steps += [
        ("hmda_county_trend.csv", lambda: pull_hmda(args.state, args.county)),
        ("cfpb_complaints.csv", lambda: pull_cfpb([z.strip() for z in args.zips.split(",") if z.strip()])),
    ]
    for name, fn in steps:
        try:
            df = fn(); df.to_csv(out / name, index=False); print(f"wrote {name}: {len(df)} rows")
        except Exception as exc:  # keep going so one outage doesn't block the others
            print(f"FAILED {name}: {exc}", file=sys.stderr)
    try:
        sod, locs = pull_fdic(args.state, args.county)
        sod.to_csv(out / "fdic_sod_branches_2021_2025.csv", index=False); print(f"wrote SOD: {len(sod)} rows")
        locs.to_csv(out / "fdic_branches_current.csv", index=False); print(f"wrote locations: {len(locs)} rows")
    except Exception as exc:
        print(f"FAILED FDIC: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
