import datetime as dt
from pathlib import Path
from pydantic import BaseModel
import litellm

from video2mdnotes.config import settings
from video2mdnotes.core.transcriber import TranscriptResult


class SummaryResult(BaseModel):
    """Represents the result of an LLM summary generation."""
    source_file: Path
    model_name: str
    summary_text: str
    generated_at: dt.datetime


def _provider_chain() -> list[tuple[str, str, str | None]]:
    """Ordered list of (provider, litellm_model, api_key) attempts.

    Driven by settings.llm_mode:
      - "openai"    (A): OpenAI only
      - "anthropic" (B): Anthropic only
      - "both"         : OpenAI first, then Anthropic as a fallback
    """
    openai = ("openai", settings.openai_model, settings.openai_api_key)
    # The "anthropic/" prefix forces litellm to route to Anthropic even for
    # model IDs newer than its built-in map (e.g. claude-haiku-4-5).
    anthropic = (
        "anthropic",
        f"anthropic/{settings.anthropic_model}",
        settings.anthropic_api_key,
    )

    mode = (settings.llm_mode or "openai").strip().lower()
    if mode == "anthropic":
        return [anthropic]
    if mode == "both":
        return [openai, anthropic]
    return [openai]  # default / "openai"


def _complete(model: str, api_key: str, system_prompt: str, user_message: str) -> str:
    """Single litellm call; raises on empty output so the caller can fall back."""
    response = litellm.completion(
        model=model,
        api_key=api_key,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        timeout=300,  # 5 minutes
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM returned an empty summary.")
    return content


def generate_summary(transcript: TranscriptResult) -> SummaryResult:
    """
    Generates a summary for a given transcript using an LLM.

    Provider selection is controlled by settings.llm_mode ("openai", "anthropic",
    or "both" for OpenAI-first-with-Anthropic-fallback). The full raw transcript
    is appended to the end of the summary.

    Raises:
        FileNotFoundError: If the prompt template file is not found.
        RuntimeError: If no configured provider could produce a summary.
    """
    if not settings.prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {settings.prompt_file}")

    # 1. Load the system prompt from the template file
    system_prompt = settings.prompt_file.read_text(encoding="utf-8")

    # 2. Prepare the user message (the full transcript)
    user_message = transcript.markdown_content

    # 3. Try each configured provider in order, falling back on failure.
    errors: list[str] = []
    for provider, model, api_key in _provider_chain():
        if not (api_key or "").strip():
            errors.append(f"{provider}: no API key configured")
            continue
        try:
            llm_output = _complete(model, api_key, system_prompt, user_message)
        except Exception as e:  # noqa: BLE001 - record and try the next provider
            errors.append(f"{provider} ({model}): {e}")
            print(f"Summarizer: {provider} failed ({e}); trying next provider if any.")
            continue

        # Append the full transcript (raw full_text, no timestamps) to the summary.
        final_summary_text = f"{llm_output}\n\n## Transcript\n{transcript.full_text}"
        return SummaryResult(
            source_file=transcript.source_file,
            model_name=model,
            summary_text=final_summary_text,
            generated_at=dt.datetime.now(),
        )

    raise RuntimeError(
        "Summary generation failed for all configured providers: " + "; ".join(errors)
    )
