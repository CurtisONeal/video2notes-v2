from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Application settings loaded from .env file and environment variables.
    """
    # LLM Provider Configuration
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

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

# Auto-detect compute type if set to 'auto'
if settings.fw_compute == "auto":
    import platform
    # Simple check for Apple Silicon
    if platform.system() == "Darwin" and platform.machine().startswith("arm"):
        settings.fw_compute = "float16"
    else:
        settings.fw_compute = "int8"
