import pytest
from pathlib import Path
from foundry.models import DemographicProfile


@pytest.fixture
def sample_demographic():
    """Sample demographic profile for testing."""
    return DemographicProfile(
        tract_geoid="48201123400",
        county_name="Harris County",
        median_household_income=35000,
        poverty_rate=0.28,
        limited_english_households_share=0.35,
        single_parent_households_share=0.22,
        unbanked_households_estimate=450,
        unbanked_share=0.08,
        mortgage_denial_rate=0.18,
        high_cost_lending_share=0.12,
        banking_complaints_per_1k=2.3,
        branch_closings_past_5_years=1,
        nearest_branch_distance_miles=0.8
    )


@pytest.fixture
def test_data_dir():
    """Path to test data."""
    return Path(__file__).parent / "data"
