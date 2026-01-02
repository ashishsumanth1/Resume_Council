"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Data directory for resume run storage
RESUME_DATA_DIR = "data/resumes"

# Data directory for saved master profiles
PROFILES_DATA_DIR = "data/master_profiles"

# Resume-specific model strategy (defaults are cost-heavy; override via env if desired)
def _env_bool(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_model_list(value: str) -> list[str]:
    return [m.strip() for m in (value or "").split(",") if m.strip()]


# If true, restore the original multi-model peer ranking (expensive).
RESUME_USE_PEER_RANKING = _env_bool("RESUME_USE_PEER_RANKING", "true")

# Draft models for Stage 1 (default: the full council / high-end)
RESUME_DRAFT_MODELS = _parse_model_list(
    os.getenv(
        "RESUME_DRAFT_MODELS",
        ",".join(COUNCIL_MODELS),
    )
)

# When peer ranking is disabled, this single model is used as judge.
RESUME_JUDGE_MODEL = os.getenv("RESUME_JUDGE_MODEL", "openai/gpt-5.1")

# If peer ranking is enabled, these models are used to rank each other (default: full council).
RESUME_RANKING_MODELS = _parse_model_list(
    os.getenv(
        "RESUME_RANKING_MODELS",
        ",".join(COUNCIL_MODELS),
    )
)

# Profile pack size (chars). Increase this to include the whole master profile.
RESUME_PROFILE_PACK_MAX_CHARS = int(os.getenv("RESUME_PROFILE_PACK_MAX_CHARS", "60000"))

# If true, do not truncate the master profile at all for resume runs.
RESUME_SEND_FULL_PROFILE = _env_bool("RESUME_SEND_FULL_PROFILE", "false")

# Optional premium polish model (only used when gating triggers)
RESUME_POLISH_MODEL = os.getenv("RESUME_POLISH_MODEL", "google/gemini-3-pro-preview")

# If score is below this, do premium polish
RESUME_POLISH_THRESHOLD = float(os.getenv("RESUME_POLISH_THRESHOLD", "0.72"))

# Token budgets
RESUME_DRAFT_MAX_TOKENS = int(os.getenv("RESUME_DRAFT_MAX_TOKENS", "900"))
RESUME_JUDGE_MAX_TOKENS = int(os.getenv("RESUME_JUDGE_MAX_TOKENS", "900"))
RESUME_POLISH_MAX_TOKENS = int(os.getenv("RESUME_POLISH_MAX_TOKENS", "900"))

# Optional style guide injected into all resume prompts.
# - Set RESUME_STYLE_GUIDE to a short inline string, OR
# - Set RESUME_STYLE_GUIDE_PATH to a text/markdown file containing your full strategy doc.
RESUME_STYLE_GUIDE = os.getenv("RESUME_STYLE_GUIDE", "")
RESUME_STYLE_GUIDE_PATH = os.getenv("RESUME_STYLE_GUIDE_PATH", "")
