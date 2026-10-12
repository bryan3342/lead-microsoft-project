"""Census ACS 5-Year (2020-2024) by census tract for the sample counties.

Tables (estimates + margins of error):
  B19001  household income brackets        B19013  median household income
  C17002  ratio of income to poverty level B11012  households by type
  B11003  family type by presence of own children
  C16002  household language by limited-English-speaking status

Processed:
  acs_tracts      one row per tract; <VAR>E estimate and <VAR>M margin of error columns
  acs_variables   variable dictionary (code -> label, table) for Power BI field descriptions

Requires CENSUS_API_KEY (environment or .env).
"""

import time

import pandas as pd

from common import SAMPLE_STATES, census_key, get, raw_dir, sample_counties, write_processed, write_provenance

VINTAGE = 2024
BASE = f"https://api.census.gov/data/{VINTAGE}/acs/acs5"
TABLES = ["B19001", "B19013", "C17002", "B11012", "B11003", "C16002"]
# Census annotation codes stored in place of a number (e.g. -666666666 = estimate not available).
SENTINELS = {-999999999, -888888888, -666666666, -555555555, -333333333, -222222222}


def fetch_table(table, state, key):
    # group() already includes NAME; requesting it separately would duplicate the column.
    params = {"get": f"group({table})", "for": "tract:*", "in": f"state:{state}", "key": key}
    # Census answers a bad key with a redirect to an HTML page rather than an error status. A newly activated
    # key is accepted by some Census servers before others, so retry a few times before giving up.
    for attempt in range(6):
        resp = get(BASE, params=params, timeout=180)
        if "invalid_key" not in resp.url:
            break
        time.sleep(5 * 2 ** attempt)
    else:
        raise SystemExit(
            "Census rejected CENSUS_API_KEY. If it's new, click the activation link in the Census signup email "
            "(keys don't work until activated), then re-run."
        )
    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    out = raw_dir("census_acs") / f"{table}_{state}.csv"
    df.to_csv(out, index=False)
    safe_params = {k: v for k, v in params.items() if k != "key"}
    write_provenance(out, BASE, safe_params, rows=len(df), extra={"vintage": f"{VINTAGE - 4}-{VINTAGE} 5-year"})
    return df


def dictionary():
    frames = []
    for table in TABLES:
        meta = get(f"{BASE}/groups/{table}.json").json()["variables"]
        for code, v in meta.items():
            if code.endswith("E") and not code.endswith("EA"):
                frames.append(
                    {"variable": code[:-1], "table": table, "concept": v.get("concept"), "label": v["label"]}
                )
    return pd.DataFrame(frames).sort_values("variable")


def main():
    key = census_key()
    if not key:
        raise SystemExit("CENSUS_API_KEY not set. Get one at https://api.census.gov/data/key_signup.html and add it to .env")

    counties = set(sample_counties())
    tracts = None
    for table in TABLES:
        parts = [fetch_table(table, state, key) for state in SAMPLE_STATES]
        df = pd.concat(parts, ignore_index=True)
        df["tract_geoid"] = df["state"] + df["county"] + df["tract"]
        df = df[df["tract_geoid"].str[:5].isin(counties)]
        keep = [c for c in df.columns if c[:6] == table and c[-1] in "EM" and not c.endswith(("EA", "MA"))]
        values = df[keep].apply(pd.to_numeric, errors="coerce")
        values = values.mask(values.isin(SENTINELS))
        table_df = pd.concat([df[["tract_geoid", "NAME"]], values], axis=1)
        tracts = table_df if tracts is None else tracts.merge(table_df.drop(columns="NAME"), on="tract_geoid", how="outer")
        print(f"  {table}: {len(table_df):,} tracts, {len(keep)} columns")

    tracts.insert(1, "county_fips", tracts["tract_geoid"].str[:5])
    write_processed(tracts.rename(columns={"NAME": "tract_name"}), "acs_tracts")
    write_processed(dictionary(), "acs_variables")


if __name__ == "__main__":
    main()
