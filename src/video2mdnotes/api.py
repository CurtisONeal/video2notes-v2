from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from video2mdnotes.config import settings
from video2mdnotes.logger import logger
from video2mdnotes.core.downloader import download_audio
from video2mdnotes.core.transcriber import transcribe_audio
from video2mdnotes.core.summarizer import generate_summary
import shutil
import datetime as dt

app = FastAPI(
    title="Video2MDNotes API",
    description="API for processing video URLs to generate markdown notes.",
)

# Configure CORS to allow requests from the Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (safe for local dev tools)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class ProcessRequest(BaseModel):
    url: HttpUrl

def process_pipeline(url: str):
    """
    The core processing pipeline, designed to be run in the background.
    This is almost identical to the CLI's process function.
    """
    logger.info(f"API: Starting background processing for URL: {url}")
    try:
        download_results = download_audio(url)
        logger.success(f"API: Downloaded {len(download_results)} videos.")

        for download_result in download_results:
            logger.info(f"API: Processing: {download_result.title}")
            transcript_result = transcribe_audio(download_result.audio_path, title=download_result.title)
            summary_result = generate_summary(transcript_result)
            
            # Archiving logic (same as CLI)
            from video2mdnotes.core.downloader import sanitize_filename
            safe_title = sanitize_filename(download_result.title)
            date_str = dt.date.today().strftime('%Y%m%d')
            project_dir_name = f"{date_str}_{safe_title}"
            project_dir = settings.output_dir / project_dir_name
            project_dir.mkdir(parents=True, exist_ok=True)

            wav_dir = project_dir / "wav_files"
            transcripts_dir = project_dir / "transcripts"
            summaries_dir = project_dir / "summaries"
            
            wav_dir.mkdir(exist_ok=True)
            transcripts_dir.mkdir(exist_ok=True)
            summaries_dir.mkdir(exist_ok=True)

            shutil.move(str(download_result.audio_path), str(wav_dir / download_result.audio_path.name))
            (transcripts_dir / f"{safe_title}.md").write_text(transcript_result.markdown_content, encoding="utf-8")
            (summaries_dir / f"{safe_title}.summary.md").write_text(summary_result.summary_text, encoding="utf-8")
            (project_dir / "original_url.txt").write_text(str(download_result.url), encoding="utf-8")
            
            logger.success(f"API: Successfully processed and archived {download_result.title}")

    except Exception as e:
        logger.error(f"API: Background processing failed for {url}. Reason: {e}")

@app.post("/process", status_code=202)
def process_video_url(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Accepts a video URL and processes it in the background.
    """
    background_tasks.add_task(process_pipeline, str(request.url))
    return {"message": "Processing started in the background. Check logs for progress."}

@app.get("/")
def read_root():
    return {"message": "Welcome to the Video2MDNotes API. Go to /docs to see the API documentation."}
