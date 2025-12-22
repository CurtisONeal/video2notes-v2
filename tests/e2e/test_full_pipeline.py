import pytest
from typer.testing import CliRunner
from pathlib import Path
import datetime as dt

from video2mdnotes.main import app
from video2mdnotes.config import settings

runner = CliRunner()

@pytest.mark.integration
def test_full_pipeline_e2e(tmp_path):
    """
    End-to-end test for the full `process` command.
    
    This test will:
    1. Download a real (but tiny) video.
    2. Transcribe it using the 'tiny' model.
    3. Summarize it using a real LLM call.
    4. Verify the final archived directory structure.
    
    Requires network access and a valid LLM API key in .env.
    """
    # Skip if no API key is present
    if not settings.openai_api_key and not settings.anthropic_api_key:
        pytest.skip("No API key found in settings. Skipping E2E test.")

    # Override settings to use temporary directories
    original_output_dir = settings.output_dir
    original_temp_dir = settings.temp_dir
    settings.output_dir = tmp_path / "output"
    settings.temp_dir = tmp_path / "temp"
    
    # Override model to 'tiny' for speed
    original_model = settings.fw_model
    settings.fw_model = "tiny"

    try:
        # A short 1-second video for testing
        test_url = "https://www.youtube.com/watch?v=tPEE9ZwTmy0"
        
        # Correct invocation for a single-command Typer app
        result = runner.invoke(app, [test_url])
        
        # 1. Check that the command executed successfully
        if result.exit_code != 0:
            print(f"CLI exited with code {result.exit_code}")
            print("--- STDOUT ---")
            print(result.stdout)
            print("--- EXCEPTION ---")
            print(result.exception)

        assert result.exit_code == 0
        assert "Processing Complete!" in result.stdout

        # 2. Verify the directory structure
        date_str = dt.date.today().strftime('%Y%m%d')
        expected_project_dir_name = f"{date_str}_shortest_video_on_youtube"
        project_dir = settings.output_dir / expected_project_dir_name
        
        assert project_dir.exists()
        assert (project_dir / "original_url.txt").exists()
        assert (project_dir / "wav_files").exists()
        assert (project_dir / "transcripts").exists()
        assert (project_dir / "summaries").exists()

        # 3. Verify the files were created
        assert len(list((project_dir / "wav_files").iterdir())) == 1
        assert len(list((project_dir / "transcripts").iterdir())) == 1
        assert len(list((project_dir / "summaries").iterdir())) == 1
        
        # Check content of URL file
        assert (project_dir / "original_url.txt").read_text() == test_url

    finally:
        # Restore original settings
        settings.output_dir = original_output_dir
        settings.temp_dir = original_temp_dir
        settings.fw_model = original_model
