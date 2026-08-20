import datetime as dt
import os
import re
import shutil
import subprocess
import tempfile
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


CLAUDE_CLI_PREFIX = "claude-cli/"

# Signatures that mean "this account is out of capacity for now", as opposed to
# an ordinary failure. The distinction matters: an ordinary failure should fall
# through to the next backend, but exhaustion must NOT silently escalate to
# metered billing — an unattended research run would spend real money without
# anyone choosing to.
_EXHAUSTION = re.compile(
    r"rate.?limit|usage limit|limit reached|out of (?:usage|credit)|quota|"
    r"too many requests|\b429\b|exceeded your|upgrade to continue",
    re.IGNORECASE,
)

# Best-effort reset-time parsing. The CLI does not guarantee any of these, so
# every branch is optional and the caller falls back to a configured default.
_RESET_ABSOLUTE = re.compile(
    r"resets?\s+at\s+(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)", re.I
)
# Durations are matched independently rather than anchored to a keyword: an
# earlier version keyed off "again|after|in" and "try again in 3 hours" matched
# on "again", then found no digits before "in" and silently gave up.
_RESET_HOURS = re.compile(r"(\d+)\s*(?:hours?|hrs?|h)\b", re.I)
_RESET_MINUTES = re.compile(r"(\d+)\s*(?:minutes?|mins?|m)\b", re.I)


class SubscriptionExhausted(Exception):
    """The subscription backend is out of capacity (not a generic failure)."""

    def __init__(self, message: str, reset_at: dt.datetime | None = None):
        super().__init__(message)
        self.reset_at = reset_at


def parse_reset_time(text: str, now: dt.datetime | None = None) -> dt.datetime | None:
    """Extract a limit-reset time from CLI error output, if it reports one."""
    now = now or dt.datetime.now()

    text = text or ""

    absolute = _RESET_ABSOLUTE.search(text)
    if absolute:
        try:
            return dt.datetime.fromisoformat(absolute.group(1).replace(" ", "T"))
        except ValueError:
            pass

    hours = _RESET_HOURS.search(text)
    minutes = _RESET_MINUTES.search(text)
    if hours or minutes:
        delta = dt.timedelta(
            hours=int(hours.group(1)) if hours else 0,
            minutes=int(minutes.group(1)) if minutes else 0,
        )
        if delta:
            return now + delta
    return None

# litellm providers that run locally / self-hosted and therefore need no API key.
LOCAL_PROVIDERS = frozenset({
    "ollama", "ollama_chat", "lm_studio", "vllm", "hosted_vllm",
    "llamafile", "xinference", "openai_like",
})


def _provider_of(model: str) -> str:
    """The provider prefix of a chain entry ('' when the entry is bare)."""
    return model.split("/", 1)[0].strip().lower() if "/" in model else ""


# .env.example ships these as literal placeholders. They are truthy, so a bare
# `if not key` check passes them straight through to the provider and the run
# fails with a confusing auth error instead of "no key configured".
_PLACEHOLDER_KEYS = frozenset({"your_key_here", "sk-...", "changeme", ""})


def real_key(value: str | None) -> str | None:
    """A configured key, or None if it is absent or a placeholder."""
    value = (value or "").strip()
    return None if value in _PLACEHOLDER_KEYS else value


def _api_key_for(model: str) -> str | None:
    """The configured key for a litellm entry, by provider prefix."""
    return real_key({
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
    }.get(_provider_of(model)))


def _complete_claude_cli(model: str, system_prompt_file: Path, user_message: str) -> str:
    """Summarize via the `claude` CLI on subscription billing (no API key).

    Two guards here are load-bearing, not tuning:

    * API keys are stripped from the child environment. With them set, the CLI
      bills the metered API instead of the subscription — the same reason
      worker.sh unsets them.
    * Tools are disabled and the child runs in a scratch cwd. `claude -p` is an
      agent: left alone it will load skills and read files, which (a) breaks the
      no-external-lookup premise the summarize prompt is written against, and
      (b) hands file/shell access to an agent processing untrusted transcript
      text. A repo cwd would also pull that repo's CLAUDE.md into the job.
    """
    alias = model[len(CLAUDE_CLI_PREFIX):].strip()
    if not alias:
        raise ValueError(f"No model alias in {model!r} (expected e.g. claude-cli/opus)")

    binary = shutil.which(settings.claude_cli_path) or settings.claude_cli_path

    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}

    with tempfile.TemporaryDirectory(prefix="v2mdnotes-summary-") as neutral_cwd:
        proc = subprocess.run(
            [
                binary, "-p",
                "--model", alias,
                "--system-prompt-file", str(system_prompt_file),
                "--disallowedTools", settings.claude_cli_disallowed_tools,
            ],
            input=user_message,
            capture_output=True,
            text=True,
            env=env,
            cwd=neutral_cwd,
            timeout=settings.claude_cli_timeout,
        )

    if proc.returncode != 0:
        combined = f"{proc.stderr or ''}\n{proc.stdout or ''}"
        detail = combined.strip()[:400]
        if _EXHAUSTION.search(combined):
            raise SubscriptionExhausted(
                f"claude CLI subscription exhausted: {detail}",
                reset_at=parse_reset_time(combined),
            )
        raise RuntimeError(f"claude CLI exited {proc.returncode}: {detail}")

    content = (proc.stdout or "").strip()
    if not content:
        raise ValueError("claude CLI returned an empty summary.")
    return content


def _complete(model: str, api_key: str | None, system_prompt: str, user_message: str) -> str:
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


EMPTY_TRANSCRIPT_PLACEHOLDER = (
    "No speech detected in this video — transcript was empty "
    "(music/text-only or silent content)."
)


def generate_summary(transcript: TranscriptResult) -> SummaryResult:
    """
    Generates a summary for a given transcript using an LLM.

    Backends are tried in settings.llm_models order. That list is a FAILOVER
    chain, not a quality ladder — entry 1 does essentially all the work and
    later entries fire only when an earlier one errors. The full raw transcript
    is appended to the end of the summary.

    If the transcript has no segments (e.g. a narration-free/music-only or silent
    source video), the LLM is not called at all — calling it on empty input causes
    it to fabricate a plausible-looking but entirely invented summary. A clear
    placeholder is returned instead.

    Raises:
        FileNotFoundError: If the prompt template file is not found.
        RuntimeError: If no configured provider could produce a summary.
    """
    if not transcript.segments:
        return SummaryResult(
            source_file=transcript.source_file,
            model_name="none",
            summary_text=EMPTY_TRANSCRIPT_PLACEHOLDER,
            generated_at=dt.datetime.now(),
        )

    if not settings.prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {settings.prompt_file}")

    # 1. Load the system prompt from the template file
    system_prompt = settings.prompt_file.read_text(encoding="utf-8")

    # 2. Prepare the user message (the full transcript)
    user_message = transcript.markdown_content

    # 3. Walk the failover chain in order, falling back on failure.
    errors: list[str] = []
    exhausted = False
    exhaustion: SubscriptionExhausted | None = None
    policy = (settings.on_exhaustion or "wait").strip().lower()

    for model in settings.llm_models:
        provider = _provider_of(model) or "unknown"

        # Once the subscription is exhausted, what may still run depends on
        # policy. The default deliberately refuses to reach a paid backend:
        # an unattended run must not start spending because nobody was there
        # to answer. main.py turns the raised exception into a wait or a stop.
        if exhausted and policy not in ("metered", "local"):
            break
        if exhausted and policy == "local" and provider not in LOCAL_PROVIDERS:
            errors.append(f"{model}: skipped (on-exhaustion=local allows local backends only)")
            continue

        try:
            if model.startswith(CLAUDE_CLI_PREFIX):
                # Subscription CLI: authenticates from the keychain, no API key.
                llm_output = _complete_claude_cli(
                    model, settings.prompt_file, user_message
                )
            elif provider in LOCAL_PROVIDERS:
                # Local models need no key, so nothing except this gate stops a
                # chain from silently falling through to a much weaker model.
                if not settings.allow_local_models:
                    errors.append(
                        f"{model}: local models disabled "
                        f"(set ALLOW_LOCAL_MODELS=true to enable)"
                    )
                    continue
                llm_output = _complete(model, None, system_prompt, user_message)
            else:
                api_key = _api_key_for(model)
                if not (api_key or "").strip():
                    errors.append(f"{model}: no API key configured")
                    continue
                llm_output = _complete(model, api_key, system_prompt, user_message)
        except SubscriptionExhausted as e:
            exhausted = True
            exhaustion = e
            errors.append(f"{model}: {e}")
            print(f"Summarizer: {model} exhausted; not escalating to a paid backend "
                  f"unless --on-exhaustion says to.")
            continue
        except Exception as e:  # noqa: BLE001 - record and try the next provider
            errors.append(f"{model}: {e}")
            print(f"Summarizer: {model} failed ({e}); trying next provider if any.")
            continue

        # Append the full transcript (raw full_text, no timestamps) to the summary.
        final_summary_text = f"{llm_output}\n\n## Transcript\n{transcript.full_text}"
        return SummaryResult(
            source_file=transcript.source_file,
            model_name=model,
            summary_text=final_summary_text,
            generated_at=dt.datetime.now(),
        )

    # Exhaustion is re-raised as itself so the caller can wait for the limit to
    # reset and retry this same video, rather than treating it as a dead run.
    if exhausted:
        raise exhaustion

    raise RuntimeError(
        "Summary generation failed for all configured providers: " + "; ".join(errors)
    )
