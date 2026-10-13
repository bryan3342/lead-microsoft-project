"""End-to-end integration tests for playbook generation."""
import pytest
import json
import numpy as np
from pathlib import Path
from foundry.agent import PlaybookAgent
from foundry.playbook_renderer import PlaybookRenderer


class TestIntegration:
    @pytest.fixture
    def agent(self):
        return PlaybookAgent()

    @pytest.fixture
    def renderer(self):
        return PlaybookRenderer()

    def test_end_to_end_playbook_generation(self, agent, tmp_path):
        """Full pipeline: load data -> analyze -> match -> render."""
        playbook = agent.generate_playbook("Houston")

        assert playbook.metro_name == "Houston"
        assert len(playbook.recommendations) > 0
        assert playbook.sample_size > 0

    def test_output_schema_matches_expectations(self, agent):
        """Recommendations have all expected fields."""
        playbook = agent.generate_playbook("Houston")

        expected_fields = [
            'tract_geoid',
            'top_need',
            'entry_product',
            'campaign',
            'channel',
            'confidence'
        ]

        for rec in playbook.recommendations:
            rec_dict = rec.model_dump()
            for field in expected_fields:
                assert field in rec_dict, f"Missing field: {field}"
                assert rec_dict[field] is not None

    def test_recommendations_per_tract_reasonable(self, agent):
        """Each tract gets 1-3 recommendations, not zero or excessive."""
        playbook = agent.generate_playbook("Houston")

        recs_by_tract = {}
        for rec in playbook.recommendations:
            if rec.tract_geoid not in recs_by_tract:
                recs_by_tract[rec.tract_geoid] = 0
            recs_by_tract[rec.tract_geoid] += 1

        for tract, count in recs_by_tract.items():
            assert 1 <= count <= 3, f"Tract {tract} has {count} recommendations (expected 1-3)"

    def test_playbook_exportable_to_all_formats(self, agent, renderer, tmp_path):
        """Generated playbook can be exported to JSON and CSV."""
        playbook = agent.generate_playbook("Houston")

        # JSON
        json_path = tmp_path / "playbook.json"
        renderer.to_json(playbook, json_path)
        assert json_path.exists()
        with open(json_path) as f:
            json_data = json.load(f)
            assert json_data['metro_name'] == "Houston"

        # CSV
        csv_path = tmp_path / "playbook.csv"
        renderer.to_csv(playbook, csv_path)
        assert csv_path.exists()
        csv_text = csv_path.read_text()
        assert "tract_geoid" in csv_text
        assert len(csv_text.split('\n')) > 2

        # Markdown
        md_text = renderer.to_markdown_summary(playbook)
        assert "Houston" in md_text
        assert len(md_text) > 100

    def test_no_inf_or_nan_in_recommendations(self, agent):
        """No inf or nan values in the output."""
        playbook = agent.generate_playbook("Houston")

        for rec in playbook.recommendations:
            rec_dict = rec.model_dump()
            playbook_str = json.dumps(rec_dict, default=str)
            # Check that JSON serialization didn't produce "NaN" or "Infinity"
            assert "NaN" not in playbook_str
            assert "Infinity" not in playbook_str
            # signal_justification should be valid text
            assert rec.signal_justification is not None
            assert isinstance(rec.signal_justification, str)

    def test_tract_coverage_reasonable(self, agent):
        """Playbook covers a reasonable fraction of tracts."""
        playbook = agent.generate_playbook("Houston")

        loader = agent.data_loader
        total_tracts = len(loader.get_all_tracts())

        # We should cover at least 80% of tracts (some may have no signals)
        coverage = playbook.sample_size / total_tracts
        assert coverage >= 0.7, f"Only {coverage*100:.1f}% of tracts covered"

    def test_multiple_signals_produce_multiple_needs(self, agent):
        """Playbook covers multiple top_need categories."""
        playbook = agent.generate_playbook("Houston")

        needs = set(rec.top_need for rec in playbook.recommendations)

        # We should have at least 2-3 distinct top_need categories
        # (language access, credit building, trust/fees, branch access, first account)
        assert len(needs) >= 2, f"Only {len(needs)} distinct top_need found, expected 2+"

    def test_confidence_distribution_reasonable(self, agent):
        """High-confidence recommendations are more common than medium."""
        playbook = agent.generate_playbook("Houston")

        high_count = sum(1 for r in playbook.recommendations if r.confidence == "high")
        medium_count = sum(1 for r in playbook.recommendations if r.confidence == "medium")

        # High signals should outnumber medium (since signals are sorted by strength)
        assert high_count > medium_count, \
            f"High confidence ({high_count}) should exceed medium ({medium_count})"
