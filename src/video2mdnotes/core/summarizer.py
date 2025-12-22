import datetime as dt
from pathlib import Path
from pydantic import BaseModel
import litellm

from video2mdnotes.config import settings
from video2mdnotes.core.transcriber import TranscriptResult

# Ensure API keys are set for litellm
# This is a good place to do it once.
litellm.api_key = settings.openai_api_key
litellm.anthropic_api_key = settings.anthropic_api_key

class SummaryResult(BaseModel):
    """Represents the result of an LLM summary generation."""
    source_file: Path
    model_name: str
    summary_text: str
    generated_at: dt.datetime

def generate_summary(transcript: TranscriptResult) -> SummaryResult:
    """
    Generates a summary for a given transcript using an LLM.
    Appends the full raw transcript to the end of the summary.

    Args:
        transcript: The TranscriptResult object containing the text to summarize.

    Returns:
        A SummaryResult object containing the summary + transcript.

    Raises:
        FileNotFoundError: If the prompt template file is not found.
        Exception: For any errors during the litellm API call.
    """
    if not settings.prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {settings.prompt_file}")

    # 1. Load the system prompt from the template file
    system_prompt = settings.prompt_file.read_text(encoding="utf-8")

    # 2. Prepare the user message (the full transcript)
    user_message = transcript.markdown_content

    # 3. Call the LLM using litellm
    try:
        response = litellm.completion(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            # Set a reasonable timeout
            timeout=300 # 5 minutes
        )
        
        # Extract the content from the response
        llm_output = response.choices[0].message.content
        
        if not llm_output:
            raise ValueError("LLM returned an empty summary.")

        # Append the full transcript to the summary
        # We use the raw full_text (no timestamps) as per requirements
        final_summary_text = f"{llm_output}\n\n## Transcript\n{transcript.full_text}"

    except Exception as e:
        # Re-raise to be handled by the orchestrator
        print(f"Error during LLM call: {e}")
        raise

    return SummaryResult(
        source_file=transcript.source_file,
        model_name=settings.llm_model,
        summary_text=final_summary_text,
        generated_at=dt.datetime.now()
    )
