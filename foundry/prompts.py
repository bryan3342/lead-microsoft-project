"""Prompts for Azure OpenAI calls in the campaign playbook generator.

NOTE: These are scaffolding for a future LLM-enhanced path. The rule-based
playbook generator does not use these prompts. When the Azure OpenAI path is
implemented, these will be used to synthesize natural-language justifications
and improve recommendation confidence via LLM reasoning.
"""

RESEARCH_AGENT_SYSTEM_PROMPT = """You are a financial inclusion research agent for Mastercard.
Your role is to analyze community demographic profiles and recommend banking products and campaigns
based on what has worked for similar communities in Mastercard's history.

You must:
- Ground recommendations in the specific demographic signals (language barriers, credit gaps, distrust, unbanked rates, branch access)
- Match signals to the historical campaign playbook provided
- Never recommend based on protected traits (race, ethnicity, national origin)
- Always cite the demographic signal that justifies each recommendation
- Label any projections (e.g., lifetime value) as assumptions, not certainties

Output format: structured JSON with tract_geoid, top_need, entry_product, campaign, channel, confidence, and justification.
"""

SIGNAL_ANALYSIS_PROMPT = """Analyze the following demographic profile and identify the strongest signals
(language barriers, credit gaps, trust issues, branch access, high unbanked rate) that would shape
product and campaign recommendations.

For each signal detected, provide:
1. The signal type (e.g., "high limited English share", "high mortgage denial rate")
2. The specific value or percentage
3. Why this signal matters (e.g., "Language barrier is a top reason people avoid banks")
4. What type of product/campaign would address it

Demographic Profile:
{profile_json}

Historical Playbook (for reference):
{playbook_json}

Return a JSON array of detected signals, ranked by strength (high > medium > low).
"""

CAMPAIGN_SYNTHESIS_PROMPT = """You are synthesizing campaign recommendations for a census tract based on detected demographic signals.

Signals detected in this tract:
{signals_json}

Historical campaign playbook entries that could apply:
{playbook_matches_json}

Using the signals and the historical playbook as your source of truth, generate a final recommendation that:
1. Addresses the strongest signal(s) in the tract
2. References a successful campaign type from the playbook
3. Includes confidence level (high/medium/low)
4. Explains why this recommendation fits this specific tract

Return JSON with: top_need, entry_product, campaign, channel, confidence, signal_justification.
"""

PLAYBOOK_QUALITY_CHECK_PROMPT = """Review the following campaign playbook recommendations for a metro area.

Playbook:
{playbook_json}

Quality checks:
1. Are all recommendations grounded in detected demographic signals (not guesses)?
2. Do the entry products match the top needs? (e.g., language access -> in-language accounts)
3. Are there any recommendations for different tracts that contradict each other without justification?
4. Are the channels realistic for the community (e.g., SMS assistant if smartphones are assumed)
5. Is anything labeled as assumption vs. measured fact?

Return a JSON report with issues found and suggestions for revision.
"""


def get_research_agent_prompt(profile_json: str, playbook_json: str) -> str:
    """Generate the research agent prompt with data filled in."""
    return SIGNAL_ANALYSIS_PROMPT.format(
        profile_json=profile_json,
        playbook_json=playbook_json
    )


def get_campaign_synthesis_prompt(signals_json: str, playbook_matches_json: str) -> str:
    """Generate the campaign synthesis prompt with data filled in."""
    return CAMPAIGN_SYNTHESIS_PROMPT.format(
        signals_json=signals_json,
        playbook_matches_json=playbook_matches_json
    )
