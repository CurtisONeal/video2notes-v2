import pytest
from pathlib import Path
from video2mdnotes.core.downloader import sanitize_filename, download_audio, DownloadResult

def test_sanitize_filename_basic():
    """Test basic filename cleaning."""
    assert sanitize_filename("Hello World") == "hello_world"
    assert sanitize_filename("My-Video-Title") == "my_video_title"

def test_sanitize_filename_complex():
    """Test removing special characters and handling mixed cases."""
    input_str = "Video #1: The Beginning! (2024)"
    # Expected: video_1_the_beginning_2024
    # Logic:
    # 1. "Video_#1:_The_Beginning!_(2024)" (spaces -> _)
    # 2. "video_#1:_the_beginning!_(2024)" (lower)
    # 3. "video_1_the_beginning_2024" (remove special chars)
    expected = "video_1_the_beginning_2024"
    assert sanitize_filename(input_str) == expected

def test_sanitize_filename_already_clean():
    """Test that an already clean filename is unchanged."""
    assert sanitize_filename("clean_filename_123") == "clean_filename_123"

@pytest.mark.integration
def test_download_audio_integration(tmp_path):
    """
    Integration test that actually downloads a small video.
    Uses a 5-second test video from YouTube.
    """
    # Override temp_dir to use pytest's tmp_path fixture
    from video2mdnotes.config import settings
    original_temp_dir = settings.temp_dir
    settings.temp_dir = tmp_path

    try:
        # A short 1-second video for testing
        test_url = "https://www.youtube.com/watch?v=tPEE9ZwTmy0"
        
        result = download_audio(test_url)

        assert isinstance(result, DownloadResult)
        assert result.audio_path.exists()
        assert result.audio_path.suffix == ".wav"
        assert result.url == test_url
        # The title of this specific video is "Shortest Video on Youtube"
        assert "shortest_video_on_youtube" in result.audio_path.name

    finally:
        # Restore settings
        settings.temp_dir = original_temp_dir
