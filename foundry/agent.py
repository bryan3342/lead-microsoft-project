"""Main orchestration agent for campaign playbook generation."""
import json
from typing import List
from foundry.models import PlaybookOutput
from foundry.data_loader import DataLoader
from foundry.signal_analyzer import SignalAnalyzer
from foundry.campaign_matcher import CampaignMatcher
from foundry.playbook_renderer import PlaybookRenderer
from foundry.config import load_azure_config, SAMPLE


class PlaybookAgent:
    """Main orchestrator for campaign playbook generation."""

    def __init__(self, sample: str = SAMPLE):
        self.sample = sample
        self.data_loader = DataLoader()
        self.analyzer = SignalAnalyzer()
        self.matcher = CampaignMatcher(self.data_loader)
        self.renderer = PlaybookRenderer()

        # Azure OpenAI (optional, for future enhancement)
        try:
            self.azure_config = load_azure_config()
        except Exception:
            self.azure_config = None
            print("Warning: Azure OpenAI not configured; using deterministic matching only")

    def generate_playbook(self, metro_name: str = "Houston") -> PlaybookOutput:
        """
        Generate a complete campaign playbook for a metro area.

        Process:
        1. Load all tracts for the metro
        2. For each tract, build demographic profile
        3. Analyze signals in the profile
        4. Match signals to campaigns
        5. Render as structured playbook
        """
        tracts = self.data_loader.get_all_tracts()
        all_recommendations = []

        for tract_geoid in tracts:
            try:
                profile = self.data_loader.get_demographic_profile(tract_geoid)
                signals = self.analyzer.analyze_signals(profile)
                recs = self.matcher.match_campaigns(tract_geoid, signals)
                all_recommendations.extend(recs)
            except Exception as e:
                # Log and skip tracts with data issues
                print(f"Warning: Could not process tract {tract_geoid}: {e}")
                continue

        playbook = self.renderer.render_playbook(metro_name, all_recommendations)
        return playbook

    def generate_and_export(
        self,
        metro_name: str = "Houston",
        output_dir: str = "output"
    ) -> str:
        """Generate playbook and export to JSON and CSV."""
        from pathlib import Path

        playbook = self.generate_playbook(metro_name)

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        json_path = output_path / f"{metro_name.lower()}_playbook.json"
        csv_path = output_path / f"{metro_name.lower()}_playbook.csv"

        self.renderer.to_json(playbook, json_path)
        self.renderer.to_csv(playbook, csv_path)

        print(f"Playbook generated:")
        print(f"  JSON: {json_path}")
        print(f"  CSV: {csv_path}")
        print(f"  Tracts: {playbook.sample_size}")
        print(f"  Recommendations: {len(playbook.recommendations)}")

        return str(json_path)

    def generate_layer2_rows(self, metro_name: str = "Houston") -> List[dict]:
        """Generate playbook and return tract-level rows in Layer 2 format."""
        playbook = self.generate_playbook(metro_name)
        return self.renderer.to_layer2_county_rows(playbook)
