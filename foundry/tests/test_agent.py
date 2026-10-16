"""Tests for PlaybookAgent: end-to-end orchestration."""
import pytest
from foundry.agent import PlaybookAgent
from foundry.models import PlaybookOutput


class TestPlaybookAgent:
    @pytest.fixture
    def agent(self):
        return PlaybookAgent()

    def test_generate_playbook(self, agent):
        """Agent generates a complete playbook for the sample metro."""
        playbook = agent.generate_playbook("Houston")

        assert isinstance(playbook, PlaybookOutput)
        assert playbook.metro_name == "Houston"
        assert playbook.sample_size > 0
        assert len(playbook.recommendations) > 0

    def test_playbook_has_required_fields(self, agent):
        """Playbook includes required fields for Power BI."""
        playbook = agent.generate_playbook("Houston")

        for rec in playbook.recommendations:
            assert rec.tract_geoid is not None
            assert rec.top_need is not None
            assert rec.entry_product is not None
            assert rec.campaign is not None
            assert rec.channel is not None
            assert rec.confidence in ["high", "medium", "low"]

    def test_no_protected_traits_in_output(self, agent):
        """Output contains no race, ethnicity, or protected attributes."""
        playbook = agent.generate_playbook("Houston")

        protected_keywords = ["race", "ethnicity", "black", "white", "hispanic", "asian"]
        playbook_str = playbook.model_dump_json().lower()

        for keyword in protected_keywords:
            assert keyword not in playbook_str, f"Found protected trait: {keyword}"

    def test_recommendations_ground_in_signals(self, agent):
        """Each recommendation has a signal justification."""
        playbook = agent.generate_playbook("Houston")

        for rec in playbook.recommendations:
            assert rec.signal_justification is not None
            assert len(rec.signal_justification) > 0

    def test_generate_layer2_rows(self, agent):
        """Generate Layer 2 format rows."""
        rows = agent.generate_layer2_rows("Houston")

        assert len(rows) > 0
        # Check that each row has the expected fields
        for row in rows[:10]:
            assert "top_need" in row
            assert "entry_product" in row
            assert "campaign" in row
            assert "channel" in row
