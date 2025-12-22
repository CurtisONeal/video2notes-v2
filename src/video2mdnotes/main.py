import typer
import shutil
import datetime as dt
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from video2mdnotes.config import settings
from video2mdnotes.logger import logger
from video2mdnotes.core.downloader import download_audio
from video2mdnotes.core.transcriber import transcribe_audio
from video2mdnotes.core.summarizer import generate_summary

app = typer.Typer(help="Video to Markdown Notes Pipeline")
console = Console()

@app.command()
def process(
    url: str = typer.Argument(..., help="The URL of the video to process"),
    keep_wav: bool = typer.Option(True, help="Keep the downloaded WAV file in the archive"),
):
    """
    Downloads, transcribes, and summarizes a video from a URL.
    """
    logger.info(f"Starting processing for URL: {url}")

    try:
        # 1. Download
        logger.info("Step 1: Downloading Audio...")
        download_result = download_audio(url)
        logger.success(f"Downloaded: {download_result.title}")

        # 2. Transcribe
        logger.info("Step 2: Transcribing Audio...")
        transcript_result = transcribe_audio(download_result.audio_path, title=download_result.title)
        logger.success(f"Transcribed: {len(transcript_result.segments)} segments")

        # 3. Summarize
        logger.info("Step 3: Generating Summary...")
        summary_result = generate_summary(transcript_result)
        logger.success("Summary Generated.")

        # 4. Archive / Output
        logger.info("Step 4: Archiving Results...")
        
        # Create project directory: YYYYMMDD_sanitized_title
        from video2mdnotes.core.downloader import sanitize_filename
        safe_title = sanitize_filename(download_result.title)
        date_str = dt.date.today().strftime('%Y%m%d')
        project_dir_name = f"{date_str}_{safe_title}"
        
        project_dir = settings.output_dir / project_dir_name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        wav_dir = project_dir / "wav_files"
        transcripts_dir = project_dir / "transcripts"
        summaries_dir = project_dir / "summaries"
        
        wav_dir.mkdir(exist_ok=True)
        transcripts_dir.mkdir(exist_ok=True)
        summaries_dir.mkdir(exist_ok=True)

        # Move/Write Files
        
        # WAV File
        dest_wav = wav_dir / download_result.audio_path.name
        if keep_wav:
            shutil.move(str(download_result.audio_path), str(dest_wav))
        else:
            download_result.audio_path.unlink()
            dest_wav = None

        # Transcript
        transcript_path = transcripts_dir / f"{safe_title}.md"
        transcript_path.write_text(transcript_result.markdown_content, encoding="utf-8")

        # Summary
        summary_path = summaries_dir / f"{safe_title}.summary.md"
        summary_path.write_text(summary_result.summary_text, encoding="utf-8")

        # Original URL
        url_file = project_dir / "original_url.txt"
        url_file.write_text(url, encoding="utf-8")

        # Final Success Message (Rich Panel)
        console.print(Panel(
            f"[bold]Processing Complete![/bold]\n\n"
            f"Output Directory: [blue]{project_dir}[/blue]\n"
            f"Summary: [blue]{summary_path}[/blue]",
            title="Success",
            border_style="green"
        ))

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
