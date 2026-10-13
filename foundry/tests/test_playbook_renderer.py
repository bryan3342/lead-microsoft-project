"""Tests for PlaybookRenderer: format and export recommendations."""
import pytest
import json
from pathlib import Path
from foundry.playbook_renderer import PlaybookRenderer
from foundry.models import CampaignRecommendation


class TestPlaybookRenderer:
    @pytest.fixture
    def renderer(self):
        return PlaybookRenderer()

    @pytest.fixture
    def sample_recommendations(self):
        return [
            CampaignRecommendation(
                tract_geoid="48201123400",
                top_need="Language access",
                entry_product="No-fee account with in-language onboarding",
                campaign="Financial education series in the community's language",
                channel="Community partners, in-language assistant",
                signal_justification="30% limited English households",
                confidence="high"
            ),
            CampaignRecommendation(
                tract_geoid="48201123401",
                top_need="Credit building",
                entry_product="Secured card",
                campaign="Credit-builder workshops",
                channel="Branch events, SMS assistant",
                signal_justification="18% mortgage denial rate",
                confidence="high"
            ),
        ]

    def test_render_playbook(self, renderer, sample_recommendations):
        """Creates a PlaybookOutput with correct metadata."""
        playbook = renderer.render_playbook("Houston", sample_recommendations)

        assert playbook.metro_name == "Houston"
        assert playbook.sample_size == 2
        assert len(playbook.recommendations) == 2
        assert "0.1.0" in playbook.metadata["version"]

    def test_to_json(self, renderer, sample_recommendations, tmp_path):
        """Exports playbook to JSON."""
        playbook = renderer.render_playbook("Houston", sample_recommendations)
        output_path = tmp_path / "playbook.json"

        renderer.to_json(playbook, output_path)

        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)
            assert data['metro_name'] == "Houston"
            assert len(data['recommendations']) == 2

    def test_to_csv(self, renderer, sample_recommendations, tmp_path):
        """Exports playbook to CSV."""
        playbook = renderer.render_playbook("Houston", sample_recommendations)
        output_path = tmp_path / "playbook.csv"

        renderer.to_csv(playbook, output_path)

        assert output_path.exists()
        lines = output_path.read_text().split('\n')
        assert "tract_geoid,top_need,entry_product,campaign,channel" in lines[0]
        assert len(lines) >= 3  # header + 2 records

    def test_to_markdown_summary(self, renderer, sample_recommendations):
        """Generates markdown summary for human review."""
        playbook = renderer.render_playbook("Houston", sample_recommendations)
        md = renderer.to_markdown_summary(playbook)

        assert "Houston" in md
        assert "Language access" in md
        assert "Credit building" in md
        assert "2 census tracts" in md

    def test_playbook_with_empty_recommendations(self, renderer):
        """Handles empty recommendation list gracefully."""
        playbook = renderer.render_playbook("Houston", [])

        assert playbook.metro_name == "Houston"
        assert playbook.sample_size == 0
        assert len(playbook.recommendations) == 0

    def test_to_layer2_county_rows(self, renderer, sample_recommendations):
        """Returns rows in a format suitable for Layer 2 display."""
        playbook = renderer.render_playbook("Houston", sample_recommendations)
        rows = renderer.to_layer2_county_rows(playbook)

        assert len(rows) == 2
        assert all("top_need" in row for row in rows)
        assert all("entry_product" in row for row in rows)
        assert all("campaign" in row for row in rows)
        assert all("channel" in row for row in rows)
