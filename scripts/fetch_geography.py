"""Geography reference tables.

- sample_counties: counties in the sample metro: the OMB 2023 delineation (published by Census), plus any
  county where FDIC BankFind still places metro branches under older boundaries (e.g. Calvert, MD for DC),
  so every branch the FDIC assigns to the metro has neighborhood data.
- zcta_tract: ZIP Code Tabulation Area -> census tract crosswalk (Census 2020 relationship file),
  used to place CFPB complaints (ZIP-level) onto tracts. Filtered to sample states.
- tract_centroids: tract internal point (lat/long) and land area (Census 2024 Gazetteer), for maps and
  for measuring distances from branches to tracts.
- tract_2010_2020: 2010 -> 2020 tract crosswalk with land-overlap shares, for HMDA 2021 (which still uses
  2010 tract boundaries).
"""

import io
import zipfile


import pandas as pd

from common import SAMPLE_CBSA, SAMPLE_STATES, get, raw_dir, write_processed, write_provenance

DELINEATION_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/"
    "2023/delineation-files/list1_2023.xlsx"
)
FDIC_LOCATIONS = "https://api.fdic.gov/banks/locations"
GAZETTEER_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_tracts_national.zip"
TRACT_2010_URL = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt"
ZCTA_TRACT_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.txt"
)


def fdic_branch_counties():
    """County FIPS -> (county name, state name) for every FDIC office tagged with the sample CBSA."""
    params = {"filters": f"CBSA_NO:{SAMPLE_CBSA}", "fields": "STCNTY,COUNTY,STNAME", "limit": 10000}
    data = get(FDIC_LOCATIONS, params=params).json()
    return {str(r["data"]["STCNTY"]).zfill(5): (r["data"]["COUNTY"], r["data"]["STNAME"]) for r in data["data"]}


def fetch_counties():
    out = raw_dir("census_geography", shared=True) / "list1_2023.xlsx"
    if not out.exists():
        out.write_bytes(get(DELINEATION_URL).content)
    all_counties = pd.read_excel(out, header=2, dtype=str)
    write_provenance(out, DELINEATION_URL, rows=len(all_counties))
    all_counties["county_fips"] = all_counties["FIPS State Code"].str.zfill(2) + all_counties["FIPS County Code"].str.zfill(3)

    omb = set(all_counties.loc[all_counties["CBSA Code"] == SAMPLE_CBSA, "county_fips"])
    fdic = fdic_branch_counties()
    df = all_counties[all_counties["county_fips"].isin(omb | set(fdic))]
    # Counties outside every 2023 metro (e.g. Madison, VA) aren't in the delineation file; name them from FDIC.
    missing = [fips for fips in fdic if fips not in set(all_counties["county_fips"])]
    extra = pd.DataFrame(
        {"county_fips": missing, "County/County Equivalent": [f"{fdic[f][0]} County" for f in missing],
         "State Name": [fdic[f][1] for f in missing]}
    )
    df = pd.concat([df, extra], ignore_index=True)
    counties = pd.DataFrame(
        {
            "county_fips": df["county_fips"],
            "county_name": df["County/County Equivalent"],
            "state": df["State Name"],
            "cbsa": df["CBSA Code"],
            "cbsa_title": df["CBSA Title"],
            "metro_division": df["Metropolitan Division Title"],
            "central_or_outlying": df["Central/Outlying County"],
            "in_omb_2023_metro": df["county_fips"].isin(omb),
            "has_fdic_metro_branches": df["county_fips"].isin(set(fdic)),
        }
    )
    write_processed(counties, "sample_counties")
    return counties


def fetch_zcta_tract():
    out = raw_dir("census_geography", shared=True) / "tab20_zcta520_tract20_natl.txt"
    if not out.exists():
        out.write_bytes(get(ZCTA_TRACT_URL, timeout=300).content)
    df = pd.read_csv(out, sep="|", dtype=str)
    write_provenance(out, ZCTA_TRACT_URL, rows=len(df))

    df = df.dropna(subset=["GEOID_ZCTA5_20"])
    df = df[df["GEOID_TRACT_20"].str[:2].isin(SAMPLE_STATES)]
    xwalk = pd.DataFrame(
        {
            "zcta": df["GEOID_ZCTA5_20"],
            "tract_geoid": df["GEOID_TRACT_20"],
            # Share of the ZCTA's land area falling in this tract; used to apportion ZIP-level counts.
            "overlap_land_m2": pd.to_numeric(df["AREALAND_PART"]),
            "zcta_land_m2": pd.to_numeric(df["AREALAND_ZCTA5_20"]),
        }
    )
    xwalk["zcta_share"] = (xwalk["overlap_land_m2"] / xwalk["zcta_land_m2"]).where(xwalk["zcta_land_m2"] > 0)
    write_processed(xwalk, "zcta_tract")


def fetch_tract_centroids():
    out = raw_dir("census_geography", shared=True) / "2024_Gaz_tracts_national.zip"
    if not out.exists():
        out.write_bytes(get(GAZETTEER_URL, timeout=300).content)
    with zipfile.ZipFile(out) as zf:
        df = pd.read_csv(zf.open(zf.namelist()[0]), sep="\t", dtype={"GEOID": str})
    df.columns = df.columns.str.strip()
    write_provenance(out, GAZETTEER_URL, rows=len(df))

    df = df[df["GEOID"].str[:2].isin(SAMPLE_STATES)]
    centroids = pd.DataFrame(
        {
            "tract_geoid": df["GEOID"],
            "latitude": df["INTPTLAT"],
            "longitude": df["INTPTLONG"],
            "land_sqmi": df["ALAND_SQMI"],
        }
    )
    write_processed(centroids, "tract_centroids")


def fetch_tract_2010_2020():
    out = raw_dir("census_geography", shared=True) / "tab20_tract20_tract10_natl.txt"
    if not out.exists():
        out.write_bytes(get(TRACT_2010_URL, timeout=300).content)
    df = pd.read_csv(out, sep="|", dtype=str, encoding="utf-8-sig")
    write_provenance(out, TRACT_2010_URL, rows=len(df))

    df = df[df["GEOID_TRACT_10"].str[:2].isin(SAMPLE_STATES)]
    part = pd.to_numeric(df["AREALAND_PART"])
    land_10 = pd.to_numeric(df["AREALAND_TRACT_10"])
    xwalk = pd.DataFrame(
        {
            "tract_2010": df["GEOID_TRACT_10"],
            "tract_2020": df["GEOID_TRACT_20"],
            # Share of the 2010 tract's land now in this 2020 tract; used to split 2010-tract counts.
            "share_of_2010_tract": (part / land_10).where(land_10 > 0),
        }
    )
    xwalk = xwalk[xwalk["share_of_2010_tract"] > 0]
    write_processed(xwalk, "tract_2010_2020")


if __name__ == "__main__":
    counties = fetch_counties()
    print(counties[["county_fips", "county_name", "state"]].to_string(index=False))
    fetch_zcta_tract()
    fetch_tract_centroids()
    fetch_tract_2010_2020()
