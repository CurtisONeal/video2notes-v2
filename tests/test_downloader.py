import pytest
from video2mdnotes.core.downloader import sanitize_filename, download_audio, DownloadResult

def test_sanitize_filename_basic():
    """Test basic filename cleaning."""
    assert sanitize_filename("Hello World") == "hello_world"
    assert sanitize_filename("My-Video-Title") == "my_video_title"

def test_sanitize_filename_complex():
    """Test removing special characters and handling mixed cases."""
    input_str = "Video #1: The Beginning! (2024)"
    expected = "video_1_the_beginning_2024"
    assert sanitize_filename(input_str) == expected

def test_sanitize_filename_already_clean():
    """Test that an already clean filename is unchanged."""
    assert sanitize_filename("clean_filename_123") == "clean_filename_123"

@pytest.mark.integration
def test_download_audio_integration_single_video(tmp_path):
    """
    Integration test that downloads a single small video.
    """
    from video2mdnotes.config import settings
    original_temp_dir = settings.temp_dir
    settings.temp_dir = tmp_path

    try:
        test_url = "https://www.youtube.com/watch?v=tPEE9ZwTmy0"
        
        results = download_audio(test_url)

        assert isinstance(results, list)
        assert len(results) == 1
        
        result = results[0]
        assert isinstance(result, DownloadResult)
        assert result.audio_path.exists()
        assert result.audio_path.suffix == ".wav"
        assert "shortest_video_on_youtube" in result.audio_path.name

    finally:
        settings.temp_dir = original_temp_dir
