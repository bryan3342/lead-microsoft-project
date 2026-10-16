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

    def test_confidence_from_playbook_when_available(self, matcher):
        """When playbook specifies confidence, use it (regardless of signal strength)."""
        signals = [
            CampaignSignal(
                signal_type="limited_english_share",
                signal_value=0.30,
                signal_strength="high",
                interpretation="30% limited English"
            )
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert recs[0].confidence == "candidate_hypothesis"

    def test_unsupported_suggestions_marked_clearly(self, matcher):
        """Unsupported suggestions are marked as such, even if signal is strong."""
        signals = [
            CampaignSignal(
                signal_type="denial_rate",
                signal_value=0.18,
                signal_strength="high",
                interpretation="18% mortgage denial rate"
            )
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert recs[0].confidence == "unsupported_suggestion"

    def test_preserves_source_evidence_for_documented_reference(self, matcher):
        """Source program and evidence fields are populated for documented signals."""
        signals = [
            CampaignSignal(
                signal_type="limited_english_share",
                signal_value=0.35,
                signal_strength="high",
                interpretation="35% limited English households"
            )
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert len(recs) == 1
        assert recs[0].source_program_name == "DiskarTech (RCBC Philippines 2022-2024)"
        assert recs[0].source_program_type == "banking_model"
        assert "25000+ cardholders" in recs[0].source_evidence
        assert "https://www.mastercard.com" in recs[0].source_evidence_url
        assert "Philippines market" in recs[0].source_caveats
        assert recs[0].local_tactic_hypothesis is not None
        assert recs[0].confidence == "candidate_hypothesis"

    def test_marks_unsupported_suggestions_clearly(self, matcher):
        """Signals without documented references are marked as unsupported_suggestion."""
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
        assert recs[0].confidence == "unsupported_suggestion"
        assert recs[0].source_program_name is None
        assert recs[0].source_evidence is None
        assert recs[0].source_caveats is None

    def test_tactic_hypothesis_describes_local_adaptation(self, matcher):
        """Local tactic hypothesis explains proposed adaptation, not Mastercard evidence."""
        signals = [
            CampaignSignal(
                signal_type="limited_english_share",
                signal_value=0.35,
                signal_strength="high",
                interpretation="35% limited English households"
            )
        ]

        recs = matcher.match_campaigns("48201123400", signals)
        assert recs[0].local_tactic_hypothesis == "Language-accessible onboarding + partner-delivered financial education (within existing bank capacity)"
        assert "DiskarTech" not in recs[0].local_tactic_hypothesis
        assert "within existing bank capacity" in recs[0].local_tactic_hypothesis
