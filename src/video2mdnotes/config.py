from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Application settings loaded from .env file and environment variables.
    """
    # LLM Provider Configuration
    #
    # llm_mode selects the summarization provider strategy (env: LLM_MODE):
    #   "openai"    (A) -> OpenAI only
    #   "anthropic" (B) -> Anthropic only
    #   "both"          -> OpenAI first, fall back to Anthropic on failure
    # Per-provider models are chosen with openai_model / anthropic_model, so you
    # can swap in a smarter or cheaper model per provider without code changes.
    llm_mode: str = "openai"
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-haiku-4-5"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Deprecated: retained for backward-compat with existing .env / docker-compose
    # (LLM_PROVIDER / LLM_MODEL). The summarizer now uses llm_mode + *_model above.
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    # faster-whisper Configuration
    fw_model: str = "medium"
    fw_compute: str = "auto" # auto, int8, float16, int8_float16
    fw_lang: str = "en"

    # File Paths (defaults are relative to project root)
    output_dir: Path = BASE_DIR / "previous_run_results"
    temp_dir: Path = BASE_DIR / "temp_files"
    prompt_file: Path = BASE_DIR / "summarize_prompt.txt"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

# Instantiate settings
settings = Settings()

# Auto-detect compute type if set to 'auto'.
# faster-whisper (ctranslate2) has no CUDA backend on macOS, so it runs on the
# CPU for BOTH Intel and Apple Silicon Macs. CPU float16 is unsupported by
# ctranslate2 and raises at model load, so int8 is the correct default here.
# (Reserve float16 for a real CUDA GPU by setting FW_COMPUTE=float16 explicitly.)
if settings.fw_compute == "auto":
    settings.fw_compute = "int8"
