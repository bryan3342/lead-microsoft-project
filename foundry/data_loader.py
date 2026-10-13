"""Load and derive per-tract demographic signals from raw ACS/HMDA/CFPB/FDIC/branch data.

Portability note: the derivation logic for limited_english_share and unbanked_share/
unbanked_households_estimate is ported from fabric/workspace/LoadPublicData.Notebook
(cell 5), which already runs this in plain pandas against the same source files. Poverty
rate, single-parent share, complaints-per-1k, and branch closings are new logic written
for this module (not present anywhere else in the repo at tract grain).
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from foundry.models import DemographicProfile
from foundry.config import SAMPLE_DATA_DIR, ASSUMPTIONS_DIR

# Years considered "recent" for branch closings; matches the Pydantic field name.
CLOSINGS_WINDOW_YEARS = 5
# HMDA/complaints loan/complaint purpose filter used by the notebook; keep identical so
# numbers match what the live dashboard already shows.
HMDA_PURPOSE_ALL = "all"


def _haversine_nearest(lat: np.ndarray, lon: np.ndarray, to_lat: np.ndarray, to_lon: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """For each (lat, lon), index of and distance in km to the nearest (to_lat, to_lon) point.

    Identical to the notebook's `nearest()` helper (fabric/workspace/LoadPublicData.Notebook,
    cell 1) so branch-closing tract assignment matches the dashboard's own approximation.
    """
    lat, lon, to_lat, to_lon = (
        np.radians(np.asarray(v, dtype=float)) for v in (lat, lon, to_lat, to_lon)
    )
    a = (
        np.sin((to_lat[None, :] - lat[:, None]) / 2) ** 2
        + np.cos(lat[:, None]) * np.cos(to_lat[None, :]) * np.sin((to_lon[None, :] - lon[:, None]) / 2) ** 2
    )
    km = 6371 * 2 * np.arcsin(np.sqrt(a))
    return km.argmin(axis=1), km.min(axis=1)


class DataLoader:
    """Load demographic, lending, complaint, and branch data; derive per-tract signals."""

    def __init__(self, sample_dir: Path = SAMPLE_DATA_DIR, assumptions_dir: Path = ASSUMPTIONS_DIR):
        self.sample_dir = sample_dir
        self.assumptions_dir = assumptions_dir
        self._acs = None
        self._signals_cache: Optional[pd.DataFrame] = None
        self._playbook_cache = None

    # ---- raw loaders -------------------------------------------------

    def load_campaign_playbook(self) -> pd.DataFrame:
        if self._playbook_cache is None:
            self._playbook_cache = pd.read_csv(self.assumptions_dir / "campaign_playbook.csv")
        return self._playbook_cache

    def _read(self, name: str) -> pd.DataFrame:
        path = self.sample_dir / f"{name}.parquet"
        return pd.read_parquet(path)

    def load_acs_tracts(self) -> pd.DataFrame:
        if self._acs is None:
            self._acs = self._read("acs_tracts")
        return self._acs

    # ---- derivation: the real work ------------------------------------

    def _build_tract_signals(self) -> pd.DataFrame:
        """Derive one row per tract with every DemographicProfile field, all vectorized."""
        acs = self.load_acs_tracts()
        households = acs["B19001_001E"]

        out = acs[["tract_geoid", "county_fips", "tract_name"]].copy()
        out["households"] = households

        out["median_household_income"] = acs["B19013_001E"]

        # Poverty rate: ratio-to-poverty-level under 1.00 (C17002 codes 002, 003) / total (001).
        # New derivation; not present elsewhere in the repo at tract grain.
        poverty_denom = acs["C17002_001E"]
        out["poverty_rate"] = (
            (acs["C17002_002E"] + acs["C17002_003E"]) / poverty_denom
        ).where(poverty_denom > 0)

        # Limited English speaking households: ported from
        # fabric/workspace/LoadPublicData.Notebook (cell 5).
        le_total = acs["C16002_001E"]
        out["limited_english_households_share"] = (
            acs[["C16002_004E", "C16002_007E", "C16002_010E", "C16002_013E"]].sum(axis=1) / le_total
        ).where(le_total > 0)

        # Single-parent household share: B11012 "no spouse or partner present, with children"
        # (female code 010, male code 015) over total households (001). New derivation.
        hh_total = acs["B11012_001E"]
        out["single_parent_households_share"] = (
            (acs["B11012_010E"] + acs["B11012_015E"]) / hh_total
        ).where(hh_total > 0)

        unbanked, underbanked = self._estimate_unbanked(acs, households)
        out["unbanked_households_estimate"] = unbanked.round(0)
        out["unbanked_share"] = (unbanked / households).where(households > 0)

        hmda = self._latest_hmda_by_tract()
        out = out.merge(hmda, on="tract_geoid", how="left")

        out["banking_complaints_per_1k"] = self._complaints_per_1k_per_year(households)
        out["branch_closings_past_5_years"] = self._closings_past_5_years()

        # Deliberately out of scope: no playbook signal depends on raw distance-to-any-branch,
        # and the notebook's only distance metric is distance-to-*target-issuer*-branch (a
        # different concept: future-tenant bank fit, not general branch access). Always None.
        out["nearest_branch_distance_miles"] = None

        # Resolve county name from county_fips
        sample_counties = self._read("sample_counties")
        county_lookup = dict(zip(sample_counties["county_fips"], sample_counties["county_name"]))
        out["county_name"] = out["county_fips"].map(county_lookup)

        return out.set_index("tract_geoid")

    def _estimate_unbanked(self, acs: pd.DataFrame, households: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Port of fabric/workspace/LoadPublicData.Notebook cell 5: apply FDIC income-bracket
        rates to ACS income-bracket household counts, then calibrate so the metro total matches
        the metro's own FDIC survey rate (data/assumptions/fdic_rates_by_income.csv +
        {sample}/fdic_survey_rates.parquet)."""
        rates = pd.read_csv(self.assumptions_dir / "fdic_rates_by_income.csv")
        survey = self._read("fdic_survey_rates")

        bracket = {
            r.income_bracket: acs[[f"{v}E" for v in r.acs_variables.split()]].sum(axis=1)
            for r in rates.itertuples()
        }
        metro = survey[
            (survey["geography_type"] == "msa")
            & (survey["year"] == survey["year"].max())
            & (survey["breakdown_var"] == "all")
            & survey["measure_var"].str.startswith("hbankstat")
        ]

        results = {}
        for status, column in (("Unbanked", "unbanked"), ("Banked: Underbanked", "underbanked")):
            estimate = sum(bracket[r.income_bracket] * getattr(r, f"{column}_rate") for r in rates.itertuples())
            factor = 1.0
            if (metro["category"] == status).any():
                metro_rate = metro.loc[metro["category"] == status, "percent"].iloc[0] / 100
                factor = metro_rate * households.sum() / estimate.sum()
            results[column] = estimate * factor
        return results["unbanked"], results["underbanked"]

    def _latest_hmda_by_tract(self) -> pd.DataFrame:
        """Load HMDA lending data for the most recent year, filter to all-purpose loans."""
        hmda = self._read("hmda_tract_year")
        hmda = hmda[hmda["loan_purpose_group"] == HMDA_PURPOSE_ALL]
        latest_year = hmda["year"].max()
        latest = hmda[hmda["year"] == latest_year]
        return latest[["tract_geoid", "denial_rate", "high_cost_share"]].rename(
            columns={"denial_rate": "mortgage_denial_rate", "high_cost_share": "high_cost_lending_share"}
        )

    def _complaints_per_1k_per_year(self, households: pd.Series) -> pd.Series:
        """Average complaints per 1,000 households per year, tract-level.

        New derivation. CFPB complaints are published by ZIP; split across a ZIP's tracts by
        land-area share (zcta_tract.csv), same approximation the notebook uses for its
        county-level complaints_per_1k. Averaged over the number of years present (rather than
        using only the latest year) because the most recent year in this sample is partial and
        produces unstable per-1k ratios when divided directly.
        """
        complaints = self._read("complaints_zip_year")
        zcta = self._read("zcta_tract")

        by_zip_year = complaints.groupby(["zip", "year"], as_index=False)["complaints"].sum()
        joined = by_zip_year.merge(zcta[["zcta", "tract_geoid", "zcta_share"]], left_on="zip", right_on="zcta")
        joined["complaints"] = joined["complaints"] * joined["zcta_share"]

        num_years = complaints["year"].nunique()
        by_tract = joined.groupby("tract_geoid", as_index=False)["complaints"].sum()
        total = by_tract.set_index("tract_geoid")["complaints"].reindex(households.index).fillna(0)
        avg_per_year = total / max(num_years, 1)
        return (avg_per_year / households * 1000).where(households > 0)

    def _closings_past_5_years(self) -> pd.Series:
        """Branch closings per tract in the last CLOSINGS_WINDOW_YEARS years.

        New derivation. branch_events.csv has no tract column. A still-open branch's uninum
        joins to branches.csv for its tract directly; a closed/sold/merged branch (not present
        in the current branches.csv snapshot) falls back to the nearest tract centroid by
        lat/long, matching the approximation fabric/workspace/LoadPublicData.Notebook (cell 7)
        already uses and documents as approximate.
        """
        events = self._read("branch_events").copy()
        events = events[events["event"] == "Branch Closing"]
        events["year"] = events["effective_date"].str[:4].astype(int)

        current_year = pd.Timestamp.now(tz="UTC").year
        events = events[events["year"] >= current_year - CLOSINGS_WINDOW_YEARS]

        branches = self._read("branches")
        br_tract = branches.set_index("uninum")["tract_geoid"]
        events["tract_geoid"] = events["uninum"].map(br_tract)

        missing = events["tract_geoid"].isna() & events["latitude"].notna()
        if missing.any():
            centroids = self._read("tract_centroids")
            idx, _ = _haversine_nearest(
                events.loc[missing, "latitude"].values,
                events.loc[missing, "longitude"].values,
                centroids["latitude"].values,
                centroids["longitude"].values,
            )
            events.loc[missing, "tract_geoid"] = centroids.iloc[idx]["tract_geoid"].values

        # Count closings per tract; fill zeros for all tracts
        closings_by_tract = events.groupby("tract_geoid").size()
        all_tracts = self.load_acs_tracts()["tract_geoid"]
        return closings_by_tract.reindex(all_tracts, fill_value=0).sort_index()

    # ---- public interface -----

    def get_all_tracts(self) -> List[str]:
        """List all tract GEOIDs in the sample."""
        if self._signals_cache is None:
            self._signals_cache = self._build_tract_signals()
        return self._signals_cache.index.tolist()

    def get_demographic_profile(self, tract_geoid: str) -> DemographicProfile:
        """Get the demographic profile for a single tract."""
        if self._signals_cache is None:
            self._signals_cache = self._build_tract_signals()
        if tract_geoid not in self._signals_cache.index:
            raise ValueError(f"Tract {tract_geoid} not found in ACS data")
        row = self._signals_cache.loc[tract_geoid]

        def _opt_float(v):
            return None if pd.isna(v) else float(v)

        def _opt_int(v):
            return None if pd.isna(v) else int(v)

        return DemographicProfile(
            tract_geoid=tract_geoid,
            county_name=str(row["county_name"]),
            households=_opt_int(row["households"]),
            median_household_income=_opt_float(row["median_household_income"]),
            poverty_rate=_opt_float(row["poverty_rate"]),
            limited_english_households_share=_opt_float(row["limited_english_households_share"]),
            single_parent_households_share=_opt_float(row["single_parent_households_share"]),
            unbanked_households_estimate=_opt_int(row["unbanked_households_estimate"]),
            unbanked_share=_opt_float(row["unbanked_share"]),
            mortgage_denial_rate=_opt_float(row.get("mortgage_denial_rate")),
            high_cost_lending_share=_opt_float(row.get("high_cost_lending_share")),
            banking_complaints_per_1k=_opt_float(row["banking_complaints_per_1k"]),
            branch_closings_past_5_years=_opt_int(row.get("branch_closings_past_5_years", 0) or 0),
            nearest_branch_distance_miles=None,
        )
