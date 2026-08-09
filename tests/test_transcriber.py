import pytest
from unittest.mock import MagicMock, patch
from video2mdnotes.core.transcriber import (
    transcribe_audio,
    build_initial_prompt,
    TranscriptResult,
    Segment,
)

# --- build_initial_prompt Tests ---

def test_build_initial_prompt_with_tags():
    """Tags are curated, so they're used directly without any frequency analysis."""
    prompt = build_initial_prompt(
        title="Introducing Claude Code",
        tags=["Claude", "Anthropic", "AI", "coding"],
        description="This description should be ignored because tags are present."
    )
    assert prompt == "Introducing Claude Code. Keywords: Claude, Anthropic, AI, coding."

def test_build_initial_prompt_caps_tags_at_fifteen():
    """Only the first 15 tags are used to keep the prompt short."""
    tags = [f"tag{i}" for i in range(20)]
    prompt = build_initial_prompt(title="Title", tags=tags)
    for i in range(15):
        assert f"tag{i}" in prompt
    for i in range(15, 20):
        assert f"tag{i}" not in prompt

def test_build_initial_prompt_falls_back_to_description_when_no_tags():
    """With no tags, fall back to a stopword-filtered word-frequency pass over the description."""
    description = "Claude Claude Claude Anthropic Anthropic coding coding coding coding the a an is"
    prompt = build_initial_prompt(title="My Video", tags=[], description=description)
    assert prompt.startswith("My Video. Keywords:")
    assert "coding" in prompt
    assert "Claude" in prompt
    assert "Anthropic" in prompt
    # Common stopwords should be filtered out.
    assert " the," not in prompt
    assert " a," not in prompt

def test_build_initial_prompt_no_tags_no_description_returns_title_only():
    """With neither tags nor a usable description, just return the title."""
    prompt = build_initial_prompt(title="Untitled Video", tags=[], description="")
    assert prompt == "Untitled Video"

def test_build_initial_prompt_filters_short_words_from_description():
    """Very short tokens (e.g. 'a', 'is', 'to') shouldn't clutter the keyword list."""
    description = "a is to in on Anthropic Anthropic Anthropic"
    prompt = build_initial_prompt(title="Video", tags=[], description=description)
    assert "Anthropic" in prompt
    assert "Keywords: Anthropic." in prompt

# --- Unit Tests (Mocked) ---

@pytest.fixture
def mock_whisper_model():
    with patch("video2mdnotes.core.transcriber.WhisperModel") as MockModel:
        # Setup the mock instance
        instance = MockModel.return_value
        
        # Mock the transcribe method return values
        # It returns (segments_generator, info)
        
        # Create a dummy segment object (similar to what faster-whisper returns)
        MockSegment = MagicMock()
        MockSegment.start = 0.0
        MockSegment.end = 2.0
        MockSegment.text = " Hello world."
        
        # Generator yields segments
        def segment_gen():
            yield MockSegment
            
        # Info object
        MockInfo = MagicMock()
        MockInfo.language = "en"
        
        instance.transcribe.return_value = (segment_gen(), MockInfo)
        
        yield MockModel

def test_transcribe_audio_mocked(mock_whisper_model, tmp_path):
    """Test the transcription logic with a mocked model."""
    # Create a dummy wav file so the existence check passes
    dummy_wav = tmp_path / "test.wav"
    dummy_wav.touch()
    
    result = transcribe_audio(dummy_wav, title="Test Video")
    
    assert isinstance(result, TranscriptResult)
    assert result.language == "en"
    assert len(result.segments) == 1
    assert result.segments[0].text == " Hello world."
    assert "Hello world" in result.markdown_content
    assert "Test Video" in result.markdown_content

# --- Integration Tests (Real Model) ---

@pytest.mark.integration
def test_transcribe_audio_integration(tmp_path):
    """
    Integration test that actually runs the Whisper model.
    Requires a valid .wav file. We'll download one first.
    """
    from video2mdnotes.core.downloader import download_audio
    from video2mdnotes.config import settings
    
    # Override temp dir
    original_temp = settings.temp_dir
    settings.temp_dir = tmp_path
    
    # Override model to 'tiny' for speed
    original_model = settings.fw_model
    settings.fw_model = "tiny"
    
    try:
        # 1. Download a tiny clip (1 sec)
        url = "https://www.youtube.com/watch?v=tPEE9ZwTmy0"
        download_results = download_audio(url)
        
        # Ensure we got a result
        assert len(download_results) == 1
        download_result = download_results[0]

        # 2. Transcribe it
        transcript_result = transcribe_audio(download_result.audio_path, title=download_result.title)
        
        # 3. Verify
        assert isinstance(transcript_result, TranscriptResult)
        assert transcript_result.source_file == download_result.audio_path
        # The video has no speech, so text might be empty or hallucinated, 
        # but the object should be valid.
        assert transcript_result.generated_at is not None
        
    finally:
        settings.temp_dir = original_temp
        settings.fw_model = original_model
