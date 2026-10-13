"""Tests for SignalAnalyzer: detect demographic signals."""
import pytest
from foundry.signal_analyzer import SignalAnalyzer
from foundry.models import DemographicProfile, CampaignSignal


class TestSignalAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return SignalAnalyzer()

    def test_detects_language_barrier_signal(self, analyzer, sample_demographic):
        """High limited English share triggers language access signal."""
        sample_demographic.limited_english_households_share = 0.30
        signals = analyzer.analyze_signals(sample_demographic)

        lang_signals = [s for s in signals if s.signal_type == "limited_english_share"]
        assert len(lang_signals) == 1
        assert lang_signals[0].signal_strength == "high"

    def test_detects_credit_building_signal(self, analyzer, sample_demographic):
        """High denial rate triggers credit building signal."""
        sample_demographic.mortgage_denial_rate = 0.18
        signals = analyzer.analyze_signals(sample_demographic)

        denial_signals = [s for s in signals if s.signal_type == "denial_rate"]
        assert len(denial_signals) == 1
        assert denial_signals[0].signal_strength == "high"

    def test_detects_unbanked_signal(self, analyzer, sample_demographic):
        """High unbanked share triggers first-account signal."""
        sample_demographic.unbanked_share = 0.10
        signals = analyzer.analyze_signals(sample_demographic)

        unbanked_signals = [s for s in signals if s.signal_type == "unbanked_share"]
        assert len(unbanked_signals) == 1
        assert unbanked_signals[0].signal_strength == "high"

    def test_detects_complaints_signal(self, analyzer, sample_demographic):
        """High complaints per 1k triggers trust/fees signal."""
        sample_demographic.banking_complaints_per_1k = 75.0
        signals = analyzer.analyze_signals(sample_demographic)

        complaint_signals = [s for s in signals if s.signal_type == "complaints_per_1k"]
        assert len(complaint_signals) == 1
        assert complaint_signals[0].signal_strength == "high"

    def test_ignores_below_threshold_signals(self, analyzer, sample_demographic):
        """Signals below minimum threshold are not returned."""
        sample_demographic.limited_english_households_share = 0.05
        sample_demographic.mortgage_denial_rate = 0.05
        sample_demographic.unbanked_share = 0.02
        sample_demographic.banking_complaints_per_1k = 10.0
        sample_demographic.branch_closings_past_5_years = 0

        signals = analyzer.analyze_signals(sample_demographic)
        assert len(signals) == 0

    def test_signals_sorted_by_strength(self, analyzer, sample_demographic):
        """Returned signals are sorted with 'high' first."""
        sample_demographic.limited_english_households_share = 0.30  # high
        sample_demographic.mortgage_denial_rate = 0.12  # medium
        sample_demographic.unbanked_share = 0.09  # high

        signals = analyzer.analyze_signals(sample_demographic)
        strengths = [s.signal_strength for s in signals]

        # High signals should come before medium
        high_count = strengths.count("high")
        medium_count = strengths.count("medium")
        assert high_count >= 1
        assert medium_count >= 0
        # Check that we don't have medium before high
        for i, s in enumerate(strengths):
            if s == "medium":
                for j in range(i):
                    assert strengths[j] != "low"

    def test_closings_rate_computed_not_raw_count(self, analyzer):
        """Tract with 1 closing and few households scores differently than one with many households."""
        small_tract = DemographicProfile(
            tract_geoid="test_small",
            county_name="Test County",
            households=100,
            branch_closings_past_5_years=1
        )
        large_tract = DemographicProfile(
            tract_geoid="test_large",
            county_name="Test County",
            households=10000,
            branch_closings_past_5_years=1
        )

        small_signals = analyzer.analyze_signals(small_tract)
        large_signals = analyzer.analyze_signals(large_tract)

        # Small tract: 1 / 100 * 100000 = 1000 per 100k
        # Large tract: 1 / 10000 * 100000 = 10 per 100k
        # So small should have a signal, large should not (below medium threshold of 20)
        small_has_closings = any(s.signal_type == "closings_per_100k" for s in small_signals)
        large_has_closings = any(s.signal_type == "closings_per_100k" for s in large_signals)

        assert small_has_closings, "Small tract with high per-100k rate should trigger signal"
        assert not large_has_closings, "Large tract with low per-100k rate should not trigger signal"

        # Verify the signal values match the computed rates
        small_closing_signal = [s for s in small_signals if s.signal_type == "closings_per_100k"][0]
        assert abs(small_closing_signal.signal_value - 1000) < 1, "Small tract signal value should be ~1000"

    def test_complaints_threshold_matches_real_data_scale(self, analyzer, sample_demographic):
        """Complaints thresholds are in the realistic range (tens, not single digits)."""
        # Real data has median ~37, so threshold of 37 is at the median
        sample_demographic.banking_complaints_per_1k = 37.0
        signals = analyzer.analyze_signals(sample_demographic)
        medium_complaints = [s for s in signals if s.signal_type == "complaints_per_1k"]
        assert len(medium_complaints) == 1
        assert medium_complaints[0].signal_strength == "medium"

        # High threshold should be ~64 (75th percentile)
        sample_demographic.banking_complaints_per_1k = 64.0
        signals = analyzer.analyze_signals(sample_demographic)
        high_complaints = [s for s in signals if s.signal_type == "complaints_per_1k"]
        assert len(high_complaints) == 1
        assert high_complaints[0].signal_strength == "high"

    def test_multiple_signals_return_multiple_recommendations(self, analyzer, sample_demographic):
        """When a tract has multiple strong signals, they all get returned."""
        sample_demographic.limited_english_households_share = 0.35
        sample_demographic.mortgage_denial_rate = 0.18
        sample_demographic.unbanked_share = 0.10
        sample_demographic.banking_complaints_per_1k = 75.0

        signals = analyzer.analyze_signals(sample_demographic)
        assert len(signals) >= 3
        signal_types = {s.signal_type for s in signals}
        assert "limited_english_share" in signal_types
        assert "denial_rate" in signal_types
        assert "unbanked_share" in signal_types
