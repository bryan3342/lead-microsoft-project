# Foundry Campaign Playbook Generator

Generates personalized campaign playbooks for US counties by matching demographic profiles to Mastercard's historical campaign data.

## Overview

The generator takes census tract demographics and produces "Layer 2: What to Buy, Where" recommendations showing which products, campaigns, and channels fit each tract. It is portable, testable, and **requires no Fabric or Azure dependency** — it works entirely locally using Python and pandas.

**Input:** Demographic data (Census ACS, FDIC survey rates, HMDA, CFPB)  
**Output:** Campaign playbook (JSON, CSV) with tract-level recommendations

## Quick Start

### Prerequisites
- Python 3.10+
- Sample data in `data/processed/{sample}/` (Houston metro included)

### Install and run

```bash
cd lead-microsoft-project
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generate playbook for Houston
python -m foundry --metro houston --format both --output output/
```

Output files:
- `output/houston_playbook.json` — Full structured playbook
- `output/houston_playbook.csv` — Tract-level recommendations

### Run tests

```bash
pytest foundry/tests/ -v
```

## Architecture

```
Data Layer (data_loader.py)
    ↓
Signal Analyzer (signal_analyzer.py) — Detect demographic needs
    ↓
Campaign Matcher (campaign_matcher.py) — Match to historical campaigns
    ↓
Playbook Renderer (playbook_renderer.py) — Format output
    ↓
Agent Orchestrator (agent.py) — Orchestrate the pipeline
```

## Key Classes

### `PlaybookAgent`
Main entry point. Orchestrates the full pipeline.

```python
from foundry.agent import PlaybookAgent
agent = PlaybookAgent(sample="houston")
playbook = agent.generate_playbook("Houston")
```

### `DataLoader`
Loads demographic data from CSVs and parquets, derives signals.

```python
from foundry.data_loader import DataLoader
loader = DataLoader()
profile = loader.get_demographic_profile("48201123400")
```

### `SignalAnalyzer`
Detects demographic signals and classifies strength.

```python
from foundry.signal_analyzer import SignalAnalyzer
analyzer = SignalAnalyzer()
signals = analyzer.analyze_signals(profile)
```

### `CampaignMatcher`
Matches signals to historical campaign recommendations.

```python
from foundry.campaign_matcher import CampaignMatcher
matcher = CampaignMatcher()
recs = matcher.match_campaigns(tract_geoid, signals)
```

## Output Format

### JSON structure
```json
{
  "metro_name": "Houston",
  "generated_at": "2026-10-13T...",
  "sample_size": 1600,
  "recommendations": [
    {
      "tract_geoid": "48201123400",
      "top_need": "Language access",
      "entry_product": "No-fee account with in-language onboarding",
      "campaign": "Financial education series in the community's language",
      "channel": "Community partners, in-language assistant",
      "signal_justification": "30.5% of households speak limited English",
      "confidence": "high"
    },
    ...
  ]
}
```

### CSV columns
- `tract_geoid` — Census tract identifier
- `top_need` — Primary community need identified
- `entry_product` — Recommended first banking product
- `campaign` — Campaign type to run
- `channel` — Outreach channel(s)
- `confidence` — Recommendation confidence (high/medium/low)
- `signal_justification` — Why this recommendation fits

## Design Principles

1. **Data-driven, not forecast-based:** Recommendations are grounded in observed demographic signals, not predictions.
2. **Fair lending:** Target by place and need only; no protected traits (race, ethnicity).
3. **Defensible:** Every recommendation cites the specific demographic signal that justifies it.
4. **Portable:** Works locally without Fabric, Azure, or any proprietary dependency.
5. **Testable:** All signal derivation and matching logic is unit-tested against real data.
6. **Transparent:** Confidence levels and signal interpretations are always included.

## Known Limitations

### `nearest_branch_distance_miles` is always `None`
Out of scope for the rule-based generator — no campaign playbook signal depends on raw distance-to-any-branch. The notebook's only distance metric is distance-to-*target-issuer* branch (a different concept: future-tenant bank fit). Not a bug; intentional by design.

### Campaign playbook is a static rule table, not mined historical performance
`data/assumptions/campaign_playbook.csv` (5 rows: signal → recommendation) encodes "what Mastercard generally recommends for this signal type," not measured lift from past campaigns. No historical-performance dataset exists in this repo yet (that's a future phase per the project spec). The *mechanism* works; the training data is thin.

### Complaints and closings use approximations
- **Complaints per 1k:** CFPB complaints are published by ZIP; we split across a ZIP's tracts by land-area share. This approximation is inherited from the notebook and documented in the notebook's own comments.
- **Branch closings:** Closed branches may not appear in the current `branches.csv` snapshot. We fall back to nearest tract by centroid distance. Same approximation as the notebook.

### Unbanked/underbanked figures are calibrated estimates
FDIC survey rates (by income bracket) are applied to ACS income-bracket household counts, then scaled so the metro total matches the metro's own FDIC survey rate (small sample, ~35–439 households per metro bracket). These are *estimates*, not measured counts. Always label as "estimated" in downstream use, consistent with the notebook's own disclaimer in `data/assumptions/README.md`.

### Azure OpenAI path is scaffolded, not implemented
`foundry/prompts.py` and the Azure config loading in `foundry/agent.py` exist for future enhancement. The live rule-based generator never calls Azure OpenAI; it falls back silently to deterministic matching. When the LLM path is built, these will be used to synthesize natural-language justifications and improve confidence scoring.

## Testing

Run all tests:
```bash
pytest foundry/tests -v
```

Run specific test file:
```bash
pytest foundry/tests/test_data_loader.py -v
```

Test coverage includes:
- Data loading and schema validation (real data regression tests)
- Signal detection accuracy
- Campaign matching logic
- Output schema correctness
- Fair lending compliance (no protected traits)
- End-to-end integration (1600+ tracts, real Houston data)

## Future Enhancements

1. **Azure OpenAI synthesis:** Use LLM to generate natural-language justifications and improve recommendation confidence.
2. **Dynamic signal thresholds:** Adjust based on metro-level baselines instead of fixed thresholds.
3. **Bank-specific customization:** Tailor recommendations to a specific bank's product offerings.
4. **Multi-language support:** Generate playbook narratives in Spanish, Mandarin, etc.
5. **Dashboard integration:** Wire playbook directly into `web/data.json` for live display.

## Troubleshooting

### Missing data for a tract
If a tract lacks census, lending, or complaints data, the analyzer will still produce recommendations based on available signals. Missing fields are set to `None` in the output.

### No recommendations generated
Check that:
1. Data files exist in `data/processed/{sample}/`
2. Demographic signals exceed minimum thresholds (see `signal_analyzer.py`'s `SIGNAL_THRESHOLDS`)
3. Campaign playbook matches signal types in the analyzer

### Azure OpenAI integration errors
If `load_azure_config()` fails, the agent falls back to deterministic matching. To enable the LLM path (once implemented), set:
```bash
export AZURE_OPENAI_KEY=your-key
export AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
export AZURE_OPENAI_DEPLOYMENT=dapa-playbook
```

## Related Files

- **Spec:** `research-data/PROJECT_CONTEXT.md`
- **Campaign Playbook:** `data/assumptions/campaign_playbook.csv`
- **Sample Data:** `data/processed/houston/`, `data/processed/dallas/`, `data/processed/dc/`
- **Assumptions:** `data/assumptions/fdic_rates_by_income.csv`, `data/assumptions/pilot_assumptions.csv`, `data/assumptions/ltv_assumptions.csv`
- **Dashboard:** `web/index.html` (currently hardcoded to Houston; can be wired to this playbook's output via a future integration PR)
