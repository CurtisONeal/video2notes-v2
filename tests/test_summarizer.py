import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import datetime as dt

from video2mdnotes.core.summarizer import generate_summary, SummaryResult
from video2mdnotes.core.transcriber import TranscriptResult
from video2mdnotes.config import settings

# --- Fixtures ---

@pytest.fixture
def mock_transcript_result(tmp_path):
    """Creates a dummy TranscriptResult for testing."""
    return TranscriptResult(
        source_file=tmp_path / "test.wav",
        language="en",
        segments=[],
        full_text="This is a test transcript.",
        markdown_content="# Test Transcript\n\nThis is a test transcript.",
        model_name="tiny",
        generated_at=dt.datetime.now()
    )

@pytest.fixture
def mock_prompt_file(tmp_path):
    """Creates a temporary prompt file and updates settings to point to it."""
    p = tmp_path / "prompt.txt"
    p.write_text("You are a summarizer.", encoding="utf-8")
    
    original_prompt_file = settings.prompt_file
    settings.prompt_file = p
    yield p
    settings.prompt_file = original_prompt_file

# --- Unit Tests (Mocked) ---

def test_generate_summary_mocked(mock_transcript_result, mock_prompt_file):
    """Test the summarization logic with a mocked LLM call (default openai mode)."""

    original_mode = settings.llm_mode
    original_key = settings.openai_api_key
    settings.llm_mode = "openai"
    settings.openai_api_key = "test-key"  # hermetic: don't depend on .env
    try:
        with patch("video2mdnotes.core.summarizer.litellm.completion") as mock_completion:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "# Summary\nThis is a summary."
            mock_completion.return_value = mock_response

            result = generate_summary(mock_transcript_result)

            # Verify result structure
            assert isinstance(result, SummaryResult)
            assert "# Summary\nThis is a summary." in result.summary_text
            assert "## Transcript\nThis is a test transcript." in result.summary_text
            assert result.model_name == settings.openai_model

            # Verify the LLM was called with correct arguments
            mock_completion.assert_called_once()
            call_kwargs = mock_completion.call_args.kwargs
            messages = call_kwargs['messages']

            # Check system prompt (from our fixture)
            assert messages[0]['role'] == 'system'
            assert messages[0]['content'] == "You are a summarizer."

            # Check user message (from transcript)
            assert messages[1]['role'] == 'user'
            assert messages[1]['content'] == mock_transcript_result.markdown_content
    finally:
        settings.llm_mode = original_mode
        settings.openai_api_key = original_key

def test_generate_summary_both_falls_back_to_anthropic(mock_transcript_result, mock_prompt_file):
    """In 'both' mode, an OpenAI failure should fall back to Anthropic."""
    saved = (settings.llm_mode, settings.openai_api_key, settings.anthropic_api_key)
    settings.llm_mode = "both"
    settings.openai_api_key = "openai-key"
    settings.anthropic_api_key = "anthropic-key"
    try:
        with patch("video2mdnotes.core.summarizer.litellm.completion") as mock_completion:
            ok = MagicMock()
            ok.choices[0].message.content = "# Summary\nFrom Anthropic."
            # First call (OpenAI) raises; second call (Anthropic) succeeds.
            mock_completion.side_effect = [RuntimeError("openai down"), ok]

            result = generate_summary(mock_transcript_result)

            assert "From Anthropic." in result.summary_text
            assert result.model_name == f"anthropic/{settings.anthropic_model}"
            assert mock_completion.call_count == 2
            # Second (successful) call routed to the anthropic-prefixed model.
            assert mock_completion.call_args_list[1].kwargs["model"] == \
                f"anthropic/{settings.anthropic_model}"
    finally:
        settings.llm_mode, settings.openai_api_key, settings.anthropic_api_key = saved


def test_generate_summary_missing_prompt_file(mock_transcript_result):
    """Test that FileNotFoundError is raised if prompt file is missing."""
    # Point settings to a non-existent file
    original_prompt_file = settings.prompt_file
    settings.prompt_file = Path("/non/existent/file.txt")
    
    try:
        with pytest.raises(FileNotFoundError):
            generate_summary(mock_transcript_result)
    finally:
        settings.prompt_file = original_prompt_file

# --- Integration Tests (Real API Call) ---

@pytest.mark.integration
def test_generate_summary_integration():
    """
    Integration test that actually calls the LLM API.
    Requires OPENAI_API_KEY (or configured provider key) in .env.
    """
    import litellm
    
    # Skip if no API key is present
    if not settings.openai_api_key and not settings.anthropic_api_key:
        pytest.skip("No API key found in settings. Skipping integration test.")

    try:
        # Simple call to verify connectivity
        response = litellm.completion(
            model=settings.llm_model,
            messages=[{"role": "user", "content": "Say 'Integration Test Passed'"}],
            max_tokens=10
        )
        content = response.choices[0].message.content
        assert content is not None
        # We don't strictly check the text because LLMs vary, but it shouldn't be empty
        assert len(content) > 0
        
    except Exception as e:
        pytest.fail(f"LLM Integration test failed: {e}")
