from pydantic import BaseModel, Field
from typing import Optional, List


class DemographicProfile(BaseModel):
    """Census tract demographic profile."""
    tract_geoid: str
    county_name: str
    households: Optional[int] = None
    median_household_income: Optional[float] = None
    poverty_rate: Optional[float] = None
    limited_english_households_share: Optional[float] = None
    single_parent_households_share: Optional[float] = None
    unbanked_households_estimate: Optional[int] = None
    unbanked_share: Optional[float] = None
    mortgage_denial_rate: Optional[float] = None
    high_cost_lending_share: Optional[float] = None
    banking_complaints_per_1k: Optional[float] = None
    branch_closings_past_5_years: Optional[int] = None
    nearest_branch_distance_miles: Optional[float] = None

    class Config:
        arbitrary_types_allowed = True


class CampaignSignal(BaseModel):
    """Detected demographic signal and its strength."""
    signal_type: str  # e.g., "limited_english_share", "denial_rate"
    signal_value: float
    signal_strength: str  # "high", "medium", "low"
    interpretation: str


class CampaignRecommendation(BaseModel):
    """Single product and campaign recommendation."""
    tract_geoid: str
    top_need: str  # e.g., "Language access", "Credit building"
    entry_product: str  # e.g., "No-fee account with in-language onboarding"
    campaign: str  # e.g., "Financial education series"
    channel: str  # e.g., "Community partners, in-language assistant"
    signal_justification: str  # Why this recommendation fits
    confidence: str  # "high", "medium", "low"


class PlaybookOutput(BaseModel):
    """Complete playbook for a metro area."""
    metro_name: str
    generated_at: str  # ISO timestamp
    sample_size: int
    recommendations: List[CampaignRecommendation]
    metadata: dict = Field(default_factory=dict)


class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI credentials and endpoint."""
    api_key: str
    api_version: str = "2024-02-15-preview"
    endpoint: str
    deployment_name: str
    model_name: str = "gpt-4"
    temperature: float = 0.3
