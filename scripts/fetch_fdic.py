"""FDIC BankFind Suite: banks, branches, branch deposits (SOD) and branch openings/closings.

Raw: data/raw/fdic_bankfind/<date>/<endpoint>.json (+ provenance with the BankFind index name/timestamp)
Processed:
  institutions      every active FDIC-insured bank, with target_issuer flag (< $10B assets)
  branches          every office in the sample metro, with census tract
  branch_deposits   Summary of Deposits per branch, 2021-latest
  branch_events     branch openings/closings in the sample counties since 2021

Location filters always use the branch's own location fields (STALPBR / OFF_PSTALP), never the
bank's headquarters fields (STALP / PSTALP).
"""

import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from common import (
    SAMPLE_CBSA,
    SAMPLE_STATES,
    START_YEAR,
    get,
    raw_dir,
    sample_counties,
    write_processed,
    write_provenance,
)

BASE = "https://api.fdic.gov/banks"
PAGE = 10000
TARGET_MAX_ASSETS = 10_000_000  # $000s, i.e. $10B: local issuers, exempt from the Reg II debit cap
GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"


def fetch_all(endpoint, filters, **extra):
    """Page through a BankFind endpoint; save raw JSON with provenance; return list of records."""
    rows, offset, meta = [], 0, None
    while True:
        params = {"filters": filters, "limit": PAGE, "offset": offset, **extra}
        payload = get(f"{BASE}/{endpoint}", params=params).json()
        meta = payload["meta"]
        rows.extend(r["data"] for r in payload["data"])
        offset += PAGE
        if offset >= meta["total"]:
            break
    out = raw_dir("fdic_bankfind") / f"{endpoint}.json"
    out.write_text(json.dumps(rows))
    write_provenance(
        out,
        f"{BASE}/{endpoint}",
        {"filters": filters, **extra},
        rows=len(rows),
        extra={"api_total": meta["total"], "fdic_index": meta.get("index")},
    )
    print(f"  {endpoint}: {len(rows):,} records (index {meta.get('index', {}).get('name')})")
    return rows


def institutions():
    df = pd.DataFrame(fetch_all("institutions", "ACTIVE:1"))
    out = df[["CERT", "FED_RSSD", "NAME", "CITY", "STALP", "ASSET", "DEP", "BKCLASS", "CBSA", "REPDTE"]].rename(
        columns=str.lower
    )
    out = out.rename(columns={"stalp": "hq_state", "asset": "assets_000", "dep": "deposits_000", "cbsa": "hq_cbsa"})
    out["target_issuer"] = out["assets_000"] < TARGET_MAX_ASSETS
    write_processed(out, "institutions")
    return out


def tract_for(lat, lon):
    params = {
        "x": lon,
        "y": lat,
        "benchmark": "Public_AR_Current",
        "vintage": "Census2020_Current",
        "layers": "Census Tracts",
        "format": "json",
    }
    try:
        tracts = get(GEOCODER, params=params, timeout=60).json()["result"]["geographies"]["Census Tracts"]
        return tracts[0]["GEOID"] if tracts else None
    except Exception:
        return None


def branches(inst):
    df = pd.DataFrame(fetch_all("locations", f"CBSA_NO:{SAMPLE_CBSA}"))
    out = pd.DataFrame(
        {
            "uninum": df["UNINUM"],
            "cert": pd.to_numeric(df["CERT"]),
            "bank_name": df["NAME"],
            "office_name": df["OFFNAME"],
            "main_office": df["MAINOFF"] == 1,
            "address": df["ADDRESS"],
            "city": df["CITY"],
            "state": df["STALP"],
            "zip": df["ZIP"].astype(str).str.zfill(5),
            "county_fips": df["STCNTY"].astype(str).str.zfill(5),
            "latitude": df["LATITUDE"],
            "longitude": df["LONGITUDE"],
            "servtype": df["SERVTYPE"],
            "servtype_desc": df["SERVTYPE_DESC"],
            # Non-MDI banks have an empty code and the description "NONE".
            "is_mdi": df["MDI_STATUS_CODE"].fillna("").astype(str).str.strip() != "",
            "mdi_status_code": df["MDI_STATUS_CODE"],
            "mdi_status_desc": df["MDI_STATUS_DESC"],
            "established": df["ESTYMD"],
        }
    )
    print(f"  geocoding {len(out):,} branches to census tracts...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        out["tract_geoid"] = list(pool.map(tract_for, out["latitude"], out["longitude"]))
    out = out.merge(inst[["cert", "fed_rssd", "assets_000", "target_issuer"]], on="cert", how="left")
    print(f"  tract match: {out['tract_geoid'].notna().mean():.1%}")
    write_processed(out, "branches")
    return out


def branch_deposits(counties):
    states = " OR ".join(SAMPLE_STATES.values())
    df = pd.DataFrame(fetch_all("sod", f"STALPBR:({states}) AND YEAR:[{START_YEAR} TO *]"))
    df["county_fips"] = df["STCNTYBR"].astype(str).str.zfill(5)
    df = df[df["county_fips"].isin(counties)]
    out = pd.DataFrame(
        {
            "year": df["YEAR"],
            "uninum": df["UNINUMBR"],
            "cert": df["CERT"],
            "bank_name": df["NAMEFULL"],
            "branch_name": df["NAMEBR"],
            "branch_number": df["BRNUM"],
            "county_fips": df["county_fips"],
            "branch_deposits_000": df["DEPSUMBR"],
            "branch_service_type": df["BRSERTYP"],
        }
    )
    write_processed(out, "branch_deposits")
    return out


def branch_events(counties):
    states = " OR ".join(SAMPLE_STATES.values())
    df = pd.DataFrame(
        fetch_all(
            "history",
            f"OFF_PSTALP:({states}) AND ORG_ROLE_CDE:BR AND EFFDATE:[{START_YEAR}-01-01 TO *]",
        )
    )
    df["county_fips"] = df["OFF_PSTNUM"].astype(int).astype(str).str.zfill(2) + df["OFF_CNTYNUM"].astype(
        int
    ).astype(str).str.zfill(3)
    df = df[df["county_fips"].isin(counties)]
    out = pd.DataFrame(
        {
            "effective_date": df["EFFDATE"].str[:10],
            "event": df["CHANGECODE_DESC"],
            "change_code": df["CHANGECODE"],
            "uninum": df["UNINUM"],
            "cert": pd.to_numeric(df["CERT"]).astype("Int64"),
            "bank_name": df["INSTNAME"],
            "office_name": df["OFF_NAME"],
            "address": df["OFF_PADDR"],
            "city": df["OFF_PCITY"],
            "zip": df["OFF_PZIP5"],
            "county_fips": df["county_fips"],
            "latitude": df["OFF_LATITUDE"],
            "longitude": df["OFF_LONGITUDE"],
            "servtype_desc": df["OFF_SERVTYPE_DESC"],
        }
    )
    write_processed(out, "branch_events")
    return out


if __name__ == "__main__":
    counties = sample_counties()
    inst = institutions()
    b = branches(inst)
    d = branch_deposits(counties)
    e = branch_events(counties)

    full = b[b["servtype"] == 11]
    target = full[full["target_issuer"]]
    print(
        f"\nSummary: {len(b):,} offices in metro; {len(full):,} full-service; "
        f"{len(target):,} at {target['cert'].nunique()} target issuers (< $10B)"
    )
    print(d.groupby("year").size().rename("deposit rows by year").to_string())
    print(e["event"].value_counts().head(8).to_string())
