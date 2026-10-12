import os
from pathlib import Path
from foundry.models import AzureOpenAIConfig

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
ASSUMPTIONS_DIR = PROJECT_ROOT / "data" / "assumptions"


def load_azure_config() -> AzureOpenAIConfig:
    """Load Azure OpenAI config from environment variables."""
    return AzureOpenAIConfig(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT", "dapa-playbook"),
        model_name=os.getenv("AZURE_OPENAI_MODEL", "gpt-4"),
        temperature=float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.3"))
    )


SAMPLE = os.getenv("SAMPLE", "houston")  # "houston", "dallas", "dc"
SAMPLE_DATA_DIR = DATA_DIR / SAMPLE
