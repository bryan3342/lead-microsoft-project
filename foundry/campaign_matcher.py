"""Match detected signals to historical campaign recommendations."""
from foundry.models import CampaignSignal, CampaignRecommendation
from foundry.data_loader import DataLoader
from typing import List
import pandas as pd
import numpy as np


class CampaignMatcher:
    """Match detected signals to Mastercard's historical campaign playbook."""

    SIGNAL_TO_PLAYBOOK_SIGNAL = {
        # Map analyzer signal types to playbook 'signal' column values
        "limited_english_share": "limited_english_share",
        "denial_rate": "denial_rate",
        "complaints_per_1k": "complaints_per_1k",
        "closings_per_100k": "closings_per_100k",
        "unbanked_share": "unbanked_share",
    }

    def __init__(self, data_loader: DataLoader = None):
        self.data_loader = data_loader or DataLoader()
        self.playbook = self.data_loader.load_campaign_playbook()

    def _safe_get(self, row, key):
        """Get value from pandas row, converting NaN to None."""
        val = row.get(key)
        if pd.isna(val):
            return None
        return val

    def match_campaigns(
        self,
        tract_geoid: str,
        signals: List[CampaignSignal]
    ) -> List[CampaignRecommendation]:
        """
        Match detected signals to campaign recommendations.

        Iterates through signals (sorted by strength) and finds corresponding
        rows in the historical playbook. Returns up to 3 recommendations
        (primary signal, secondary if available, tertiary if available).
        """
        recommendations = []

        for signal in signals:
            # Map signal type to playbook signal name
            playbook_signal = self.SIGNAL_TO_PLAYBOOK_SIGNAL.get(signal.signal_type)
            if not playbook_signal:
                continue

            # Find matching row in playbook
            match = self.playbook[self.playbook['signal'] == playbook_signal]
            if match.empty:
                continue

            match_row = match.iloc[0]

            # Get confidence from playbook or infer from signal strength
            confidence = self._safe_get(match_row, 'confidence')
            if not confidence:
                confidence = "high" if signal.signal_strength == "high" else "medium"

            recommendation = CampaignRecommendation(
                tract_geoid=tract_geoid,
                top_need=match_row['top_need'],
                entry_product=match_row['entry_product'],
                campaign=match_row['campaign'],
                channel=match_row['channel'],
                signal_justification=signal.interpretation,
                confidence=confidence,
                source_program_name=self._safe_get(match_row, 'source_program_name'),
                source_program_type=self._safe_get(match_row, 'source_program_type'),
                source_evidence=self._safe_get(match_row, 'source_evidence'),
                source_evidence_url=self._safe_get(match_row, 'source_evidence_url'),
                source_caveats=self._safe_get(match_row, 'source_caveats'),
                local_tactic_hypothesis=self._safe_get(match_row, 'local_tactic_hypothesis')
            )
            recommendations.append(recommendation)

            # Limit to 3 recommendations per tract
            if len(recommendations) >= 3:
                break

        return recommendations
