"""Format campaign recommendations as structured playbooks."""
from foundry.models import CampaignRecommendation, PlaybookOutput
from typing import List
from datetime import datetime
import json
import csv
from pathlib import Path


class PlaybookRenderer:
    """Format campaign recommendations as structured playbooks."""

    def render_playbook(
        self,
        metro_name: str,
        recommendations: List[CampaignRecommendation]
    ) -> PlaybookOutput:
        """Create a PlaybookOutput from a list of recommendations."""
        return PlaybookOutput(
            metro_name=metro_name,
            generated_at=datetime.utcnow().isoformat() + "Z",
            sample_size=len(set(r.tract_geoid for r in recommendations)),
            recommendations=recommendations,
            metadata={
                "version": "0.1.0",
                "layer": "Layer 2: What to Buy, Where",
                "description": "Recommended product and campaign mix for each census tract"
            }
        )

    def to_json(self, playbook: PlaybookOutput, output_path: Path) -> None:
        """Export playbook to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(playbook.model_dump_json(indent=2))

    def to_csv(self, playbook: PlaybookOutput, output_path: Path) -> None:
        """Export playbook recommendations to CSV (Layer 2 format)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for rec in playbook.recommendations:
            rows.append({
                "tract_geoid": rec.tract_geoid,
                "top_need": rec.top_need,
                "entry_product": rec.entry_product,
                "campaign": rec.campaign,
                "channel": rec.channel,
                "confidence": rec.confidence,
                "signal_justification": rec.signal_justification,
                "source_program_name": rec.source_program_name or "",
                "source_program_type": rec.source_program_type or "",
                "source_evidence": rec.source_evidence or "",
                "source_evidence_url": rec.source_evidence_url or "",
                "source_caveats": rec.source_caveats or "",
                "local_tactic_hypothesis": rec.local_tactic_hypothesis or "",
            })

        if not rows:
            return

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def to_markdown_summary(self, playbook: PlaybookOutput) -> str:
        """Export playbook as markdown summary (for human review)."""
        lines = [
            f"# Campaign Playbook: {playbook.metro_name}",
            f"Generated: {playbook.generated_at}",
            f"Sample size: {playbook.sample_size} census tracts",
            "",
            "## Recommended Product and Campaign Mix",
            ""
        ]

        # Group by top_need for readability
        by_need = {}
        for rec in playbook.recommendations:
            if rec.top_need not in by_need:
                by_need[rec.top_need] = []
            by_need[rec.top_need].append(rec)

        for need, recs in by_need.items():
            lines.append(f"### {need}")
            lines.append(f"Areas with this need: {len(recs)} tracts")
            lines.append(f"- **Product:** {recs[0].entry_product}")
            lines.append(f"- **Campaign:** {recs[0].campaign}")
            lines.append(f"- **Channel:** {recs[0].channel}")
            lines.append("")

        return "\n".join(lines)

    def to_layer2_county_rows(self, playbook: PlaybookOutput) -> List[dict]:
        """Convenience adapter: aggregate tract-level recommendations to county level.

        Groups by tract's county_name (implicitly available via the notebook's
        county-resolution in data_loader), picks the most frequent top_need per county,
        and returns rows in the shape web/index.html's Layer 2 table expects:
        area, top_need, entry_product, campaign, channel (omit times_metro/value
        since those require the LTV model, out of scope for this rule-based generator).
        """
        # For now, this is a pass-through: return tracts grouped by area name if available
        # Full county aggregation would require county name to be carried through the
        # recommendation, which it currently is not. This is a placeholder for future enhancement.
        rows = []
        for rec in playbook.recommendations:
            rows.append({
                "tract_geoid": rec.tract_geoid,
                "top_need": rec.top_need,
                "entry_product": rec.entry_product,
                "campaign": rec.campaign,
                "channel": rec.channel,
            })
        return rows
