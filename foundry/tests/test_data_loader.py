"""Tests for the DataLoader: load and derive demographic signals."""
import pytest
import pandas as pd
import numpy as np
from foundry.data_loader import DataLoader
from foundry.config import SAMPLE_DATA_DIR


class TestDataLoader:
    @pytest.fixture
    def loader(self):
        return DataLoader(sample_dir=SAMPLE_DATA_DIR)

    def test_load_campaign_playbook(self, loader):
        """Campaign playbook loads and has expected columns."""
        playbook = loader.load_campaign_playbook()
        assert not playbook.empty
        assert "signal" in playbook.columns
        assert "top_need" in playbook.columns
        assert "entry_product" in playbook.columns
        assert "campaign" in playbook.columns
        assert "channel" in playbook.columns
        assert len(playbook) == 5  # Five signals in the standard playbook

    def test_load_acs_tracts(self, loader):
        """ACS data loads as parquet."""
        acs = loader.load_acs_tracts()
        assert not acs.empty
        assert "tract_geoid" in acs.columns
        assert len(acs) > 1000  # Houston has 1600+ tracts

    def test_get_demographic_profile(self, loader):
        """Can fetch a demographic profile for a known tract."""
        tracts = loader.get_all_tracts()
        assert len(tracts) > 0

        first_tract = tracts[0]
        profile = loader.get_demographic_profile(first_tract)
        assert profile.tract_geoid == first_tract
        assert profile.county_name is not None
        assert profile.households is not None

    def test_get_demographic_profile_missing_tract(self, loader):
        """Raises ValueError for unknown tract."""
        with pytest.raises(ValueError):
            loader.get_demographic_profile("99999999999")

    def test_poverty_rate_in_valid_range(self, loader):
        """Poverty rate is always in [0, 1] where defined."""
        tracts = loader.get_all_tracts()
        for tract in tracts[:100]:  # Sample check; full check too slow
            profile = loader.get_demographic_profile(tract)
            if profile.poverty_rate is not None:
                assert 0 <= profile.poverty_rate <= 1, f"Tract {tract} poverty rate {profile.poverty_rate} out of range"

    def test_limited_english_share_matches_notebook_reference(self, loader):
        """Limited English share metro-wide mean matches verified notebook value."""
        tracts = loader.get_all_tracts()
        shares = []
        for tract in tracts:
            profile = loader.get_demographic_profile(tract)
            if profile.limited_english_households_share is not None:
                shares.append(profile.limited_english_households_share)

        assert len(shares) > 0
        metro_mean = sum(shares) / len(shares)
        # Verified value from notebook: ~0.104, allow ±0.01 tolerance
        assert 0.094 <= metro_mean <= 0.114, f"Limited English metro mean {metro_mean} outside expected range"

    def test_unbanked_calibration_within_metro_tolerance(self, loader):
        """Metro-wide unbanked households match FDIC survey rate within tolerance."""
        loader._signals_cache = None  # Force rebuild
        acs = loader.load_acs_tracts()
        households_total = acs["B19001_001E"].sum()

        tracts = loader.get_all_tracts()
        unbanked_total = 0
        for tract in tracts:
            profile = loader.get_demographic_profile(tract)
            if profile.unbanked_households_estimate is not None:
                unbanked_total += profile.unbanked_households_estimate

        metro_unbanked_rate = unbanked_total / households_total
        # Verified from data/processed/houston/fdic_survey_rates.csv: metro rate ~0.0938, allow ±0.01
        assert 0.0838 <= metro_unbanked_rate <= 0.1038, \
            f"Metro unbanked rate {metro_unbanked_rate} outside tolerance"

    def test_complaints_per_1k_no_inf_or_nan_blowup(self, loader):
        """Complaints per 1k has no inf or nan values."""
        tracts = loader.get_all_tracts()
        for tract in tracts[:200]:  # Sample
            profile = loader.get_demographic_profile(tract)
            if profile.banking_complaints_per_1k is not None:
                assert not pd.isna(profile.banking_complaints_per_1k), \
                    f"Tract {tract} complaints_per_1k is NaN"
                assert not np.isinf(profile.banking_complaints_per_1k), \
                    f"Tract {tract} complaints_per_1k is inf"

    def test_branch_closings_nonnegative_and_bounded(self, loader):
        """Branch closings per tract are non-negative and reasonable."""
        tracts = loader.get_all_tracts()
        for tract in tracts[:500]:  # Sample, full iteration too slow
            profile = loader.get_demographic_profile(tract)
            if profile.branch_closings_past_5_years is not None:
                assert profile.branch_closings_past_5_years >= 0, \
                    f"Tract {tract} has negative closings count"
                # Sanity upper bound: no tract should have more than 50 closings in 5 years
                assert profile.branch_closings_past_5_years <= 50, \
                    f"Tract {tract} has implausibly high closings: {profile.branch_closings_past_5_years}"

    def test_county_name_resolved_not_unknown(self, loader):
        """County name is always resolved, never 'Unknown'."""
        tracts = loader.get_all_tracts()
        for tract in tracts[:100]:
            profile = loader.get_demographic_profile(tract)
            assert profile.county_name is not None
            assert profile.county_name != "Unknown", \
                f"Tract {tract} county name not resolved"
            # Should be one of the Houston-area counties
            assert "County" in profile.county_name or profile.county_name in ["Harris", "Fort Bend", "Montgomery", "Galveston"], \
                f"Tract {tract} has unexpected county name: {profile.county_name}"

    def test_households_field_populated(self, loader):
        """Households field is always populated for inhabited tracts."""
        tracts = loader.get_all_tracts()
        inhabited_count = 0
        for tract in tracts[:100]:
            profile = loader.get_demographic_profile(tract)
            assert profile.households is not None
            # Some tracts may be water/non-residential with 0 households; skip those
            if profile.households > 0:
                inhabited_count += 1
        # Sanity check: we should have found some inhabited tracts in Houston
        assert inhabited_count > 50, f"Too few inhabited tracts found in sample: {inhabited_count}"

    def test_nearest_branch_distance_always_none(self, loader):
        """Nearest branch distance is intentionally always None (out of scope)."""
        tracts = loader.get_all_tracts()
        for tract in tracts[:50]:
            profile = loader.get_demographic_profile(tract)
            assert profile.nearest_branch_distance_miles is None
