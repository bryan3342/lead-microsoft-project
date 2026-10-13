"""Detect and score demographic signals that map to campaigns."""
from foundry.models import DemographicProfile, CampaignSignal
from typing import List


class SignalAnalyzer:
    """Detect and score demographic signals that map to campaigns."""

    SIGNAL_THRESHOLDS = {
        # High thresholds mean the signal is strong; low means weak.
        # Verified against Houston data; see data_loader tests for regression checks.
        "limited_english_share": {"high": 0.25, "medium": 0.15},
        "denial_rate": {"high": 0.15, "medium": 0.10},
        "complaints_per_1k": {"high": 64, "medium": 37},
        "closings_per_100k": {"high": 50, "medium": 20},
        "unbanked_share": {"high": 0.08, "medium": 0.05},
    }

    def analyze_signals(self, profile: DemographicProfile) -> List[CampaignSignal]:
        """
        Detect which signals are present and strong in a demographic profile.

        Returns a list of CampaignSignal objects, sorted by strength (high first).
        """
        signals = []

        # Limited English speakers (language access need)
        if profile.limited_english_households_share is not None:
            strength = self._classify_strength(
                profile.limited_english_households_share,
                self.SIGNAL_THRESHOLDS["limited_english_share"]
            )
            if strength:
                signals.append(CampaignSignal(
                    signal_type="limited_english_share",
                    signal_value=profile.limited_english_households_share,
                    signal_strength=strength,
                    interpretation=f"{profile.limited_english_households_share*100:.1f}% of households speak limited English at home"
                ))

        # High mortgage denial rate (credit gap)
        if profile.mortgage_denial_rate is not None:
            strength = self._classify_strength(
                profile.mortgage_denial_rate,
                self.SIGNAL_THRESHOLDS["denial_rate"]
            )
            if strength:
                signals.append(CampaignSignal(
                    signal_type="denial_rate",
                    signal_value=profile.mortgage_denial_rate,
                    signal_strength=strength,
                    interpretation=f"Mortgage denial rate {profile.mortgage_denial_rate*100:.1f}% (high denial rate indicates credit building need)"
                ))

        # Banking complaints (trust issue)
        if profile.banking_complaints_per_1k is not None:
            strength = self._classify_strength(
                profile.banking_complaints_per_1k,
                self.SIGNAL_THRESHOLDS["complaints_per_1k"]
            )
            if strength:
                signals.append(CampaignSignal(
                    signal_type="complaints_per_1k",
                    signal_value=profile.banking_complaints_per_1k,
                    signal_strength=strength,
                    interpretation=f"{profile.banking_complaints_per_1k:.1f} banking complaints per 1,000 residents (trust and fees issue)"
                ))

        # Branch closings (access issue) — compute per-100k rate
        if profile.branch_closings_past_5_years is not None and profile.households and profile.households > 0:
            closings_per_100k = profile.branch_closings_past_5_years / profile.households * 100000
            strength = self._classify_strength(
                closings_per_100k,
                self.SIGNAL_THRESHOLDS["closings_per_100k"]
            )
            if strength:
                signals.append(CampaignSignal(
                    signal_type="closings_per_100k",
                    signal_value=closings_per_100k,
                    signal_strength=strength,
                    interpretation=f"{profile.branch_closings_past_5_years} branch closing(s) in 5 years "
                                   f"({closings_per_100k:.0f} per 100k households, branch access issue)"
                ))

        # High unbanked rate
        if profile.unbanked_share is not None:
            strength = self._classify_strength(
                profile.unbanked_share,
                self.SIGNAL_THRESHOLDS["unbanked_share"]
            )
            if strength:
                signals.append(CampaignSignal(
                    signal_type="unbanked_share",
                    signal_value=profile.unbanked_share,
                    signal_strength=strength,
                    interpretation=f"~{profile.unbanked_share*100:.1f}% of households are estimated unbanked (needs first account and trust-building)"
                ))

        # Sort by strength: high > medium > low
        strength_order = {"high": 0, "medium": 1, "low": 2}
        signals.sort(key=lambda s: strength_order.get(s.signal_strength, 3))

        return signals

    def _classify_strength(self, value: float, thresholds: dict) -> str:
        """Classify signal strength as 'high', 'medium', or None (below minimum)."""
        if value >= thresholds["high"]:
            return "high"
        elif value >= thresholds["medium"]:
            return "medium"
        else:
            return None
