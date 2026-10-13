"""Tests for CampaignMatcher: map signals to playbook recommendations."""
import pytest
from foundry.campaign_matcher import CampaignMatcher
from foundry.models import CampaignSignal


class TestCampaignMatcher:
    @pytest.fixture
    def matcher(self):
        return CampaignMatcher()

    def test_matches_language_signal_to_campaign(self, matcher):
        """Language barrier signal maps to language-access campaign."""
        signals = [
            CampaignSignal(
                signal_type="limited_english_share",
                signal_value=0.30,
                signal_strength="high",
                interpretation="30% limited English households"
            )
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert len(recs) == 1
        assert "language" in recs[0].top_need.lower() or "language" in recs[0].entry_product.lower()

    def test_matches_credit_signal_to_campaign(self, matcher):
        """High denial rate signal maps to credit-builder campaign."""
        signals = [
            CampaignSignal(
                signal_type="denial_rate",
                signal_value=0.18,
                signal_strength="high",
                interpretation="18% mortgage denial rate"
            )
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert len(recs) == 1
        assert "credit" in recs[0].top_need.lower() or "credit" in recs[0].entry_product.lower()

    def test_matches_unbanked_signal(self, matcher):
        """Unbanked signal maps to first-account campaign."""
        signals = [
            CampaignSignal(
                signal_type="unbanked_share",
                signal_value=0.10,
                signal_strength="high",
                interpretation="10% unbanked households"
            )
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert len(recs) == 1
        assert "first" in recs[0].top_need.lower() or "account" in recs[0].entry_product.lower()

    def test_limits_to_three_recommendations(self, matcher):
        """Returns at most 3 recommendations per tract."""
        signals = [
            CampaignSignal(signal_type="limited_english_share", signal_value=0.30, signal_strength="high", interpretation="Test"),
            CampaignSignal(signal_type="denial_rate", signal_value=0.18, signal_strength="high", interpretation="Test"),
            CampaignSignal(signal_type="complaints_per_1k", signal_value=75.0, signal_strength="high", interpretation="Test"),
            CampaignSignal(signal_type="unbanked_share", signal_value=0.10, signal_strength="high", interpretation="Test"),
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert len(recs) <= 3

    def test_empty_signals_returns_empty_recommendations(self, matcher):
        """No signals yields no recommendations."""
        recs = matcher.match_campaigns("48201123400", [])
        assert len(recs) == 0

    def test_confidence_high_for_high_strength_signals(self, matcher):
        """High-strength signals get high confidence recommendations."""
        signals = [
            CampaignSignal(
                signal_type="limited_english_share",
                signal_value=0.30,
                signal_strength="high",
                interpretation="30% limited English"
            )
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert recs[0].confidence == "high"

    def test_confidence_medium_for_medium_strength_signals(self, matcher):
        """Medium-strength signals get medium confidence recommendations."""
        signals = [
            CampaignSignal(
                signal_type="limited_english_share",
                signal_value=0.20,
                signal_strength="medium",
                interpretation="20% limited English"
            )
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert recs[0].confidence == "medium"
