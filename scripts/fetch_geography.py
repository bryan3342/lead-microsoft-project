"""Geography reference tables.

- sample_counties: counties in the sample metro (OMB 2023 delineation, published by Census).
- zcta_tract: ZIP Code Tabulation Area -> census tract crosswalk (Census 2020 relationship file),
  used to place CFPB complaints (ZIP-level) onto tracts. Filtered to sample states.
"""

import pandas as pd

from common import SAMPLE_CBSA, SAMPLE_STATES, get, raw_dir, write_processed, write_provenance

DELINEATION_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/"
    "2023/delineation-files/list1_2023.xlsx"
)
ZCTA_TRACT_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.txt"
)


def fetch_counties():
    out = raw_dir("census_geography") / "list1_2023.xlsx"
    out.write_bytes(get(DELINEATION_URL).content)
    df = pd.read_excel(out, header=2, dtype=str)
    write_provenance(out, DELINEATION_URL, rows=len(df))

    df = df[df["CBSA Code"] == SAMPLE_CBSA]
    counties = pd.DataFrame(
        {
            "county_fips": df["FIPS State Code"].str.zfill(2) + df["FIPS County Code"].str.zfill(3),
            "county_name": df["County/County Equivalent"],
            "state": df["State Name"],
            "cbsa": df["CBSA Code"],
            "cbsa_title": df["CBSA Title"],
            "metro_division": df["Metropolitan Division Title"],
            "central_or_outlying": df["Central/Outlying County"],
        }
    )
    write_processed(counties, "sample_counties")
    return counties


def fetch_zcta_tract():
    out = raw_dir("census_geography") / "tab20_zcta520_tract20_natl.txt"
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


if __name__ == "__main__":
    counties = fetch_counties()
    print(counties[["county_fips", "county_name", "state"]].to_string(index=False))
    fetch_zcta_tract()
