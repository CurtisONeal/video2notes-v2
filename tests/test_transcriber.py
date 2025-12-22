import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from video2mdnotes.core.transcriber import transcribe_audio, TranscriptResult, Segment

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
        download_result = download_audio(url)
        
        # 2. Transcribe it
        transcript_result = transcribe_audio(download_result.audio_path, title=download_result.title)
        
        # 3. Verify
        assert isinstance(transcript_result, TranscriptResult)
        assert transcript_result.source_file == download_result.audio_path
        # The video has no speech, so text might be empty or hallucinated, 
        # but the object should be valid.
        # Let's just check that we got a result.
        assert transcript_result.generated_at is not None
        
    finally:
        settings.temp_dir = original_temp
        settings.fw_model = original_model
