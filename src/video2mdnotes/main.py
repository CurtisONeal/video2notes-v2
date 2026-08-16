import typer
import shutil
import datetime as dt
from rich.console import Console
from rich.panel import Panel

from video2mdnotes.config import settings
from video2mdnotes.logger import logger
from video2mdnotes.core.downloader import DownloadResult, fetch_audio, probe_source
from video2mdnotes.core.transcriber import transcribe_audio, build_initial_prompt
from video2mdnotes.core.summarizer import generate_summary
from video2mdnotes.core.captions import transcript_from_captions

app = typer.Typer(help="Video to Markdown Notes Pipeline")
console = Console()

@app.command()
def process(
    url: str = typer.Argument(..., help="The URL of the video or playlist to process"),
    keep_wav: bool = typer.Option(True, help="Keep the downloaded WAV file in the archive"),
):
    """
    Downloads, transcribes, and summarizes a video or playlist from a URL.
    """
    logger.info(f"Starting processing for URL: {url}")

    try:
        # 1. Probe (metadata + caption availability; no audio yet)
        logger.info("Step 1: Probing source...")
        sources = probe_source(url)
        logger.success(f"Found {len(sources)} videos.")

        for source in sources:
            logger.info(f"Processing: {source.title}")

            # 2. Transcript — captions first, Whisper as the fallback.
            logger.info("Step 2: Obtaining Transcript...")
            transcript_result = None
            if settings.captions_first:
                transcript_result = transcript_from_captions(
                    title=source.title, subtitles=source.subtitles
                )
                if transcript_result is None and source.has_automatic_captions:
                    logger.info(
                        "Only machine captions available — using Whisper instead "
                        "(auto-captions are ASR without our vocabulary hint)."
                    )

            audio_path = None
            if transcript_result is None:
                audio_path = fetch_audio(source)
                initial_prompt = build_initial_prompt(
                    title=source.title,
                    tags=source.tags,
                    description=source.description
                )
                transcript_result = transcribe_audio(
                    audio_path,
                    title=source.title,
                    initial_prompt=initial_prompt
                )

            download_result = DownloadResult(
                audio_path=audio_path,
                title=source.title,
                url=source.url,
                download_date=dt.date.today(),
                tags=source.tags,
                description=source.description,
            )
            logger.success(
                f"Transcript ready via {transcript_result.transcript_source}: "
                f"{len(transcript_result.segments)} segments"
            )

            # 3. Summarize
            logger.info("Step 3: Generating Summary...")
            summary_result = generate_summary(transcript_result)
            logger.success("Summary Generated.")

            # 4. Archive / Output
            logger.info("Step 4: Archiving Results...")
            
            from video2mdnotes.core.downloader import sanitize_filename
            safe_title = sanitize_filename(download_result.title)
            date_str = dt.date.today().strftime('%Y%m%d')
            project_dir_name = f"{date_str}_{safe_title}"
            
            project_dir = settings.output_dir / project_dir_name
            project_dir.mkdir(parents=True, exist_ok=True)

            transcripts_dir = project_dir / "transcripts"
            summaries_dir = project_dir / "summaries"

            transcripts_dir.mkdir(exist_ok=True)
            summaries_dir.mkdir(exist_ok=True)

            # No audio exists on the captions path — nothing to archive or clean up.
            dest_wav = None
            if download_result.audio_path is not None:
                wav_dir = project_dir / "wav_files"
                wav_dir.mkdir(exist_ok=True)
                if keep_wav:
                    dest_wav = wav_dir / download_result.audio_path.name
                    shutil.move(str(download_result.audio_path), str(dest_wav))
                else:
                    download_result.audio_path.unlink()

            transcript_path = transcripts_dir / f"{safe_title}.md"
            transcript_path.write_text(transcript_result.markdown_content, encoding="utf-8")

            summary_path = summaries_dir / f"{safe_title}.summary.md"
            summary_path.write_text(summary_result.summary_text, encoding="utf-8")

            url_file = project_dir / "original_url.txt"
            url_file.write_text(download_result.url, encoding="utf-8")

            console.print(Panel(
                f"[bold]Processing Complete for {download_result.title}![/bold]\n\n"
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
