import re
import datetime as dt
from pathlib import Path
from pydantic import BaseModel
import yt_dlp

from video2mdnotes.config import settings

class DownloadResult(BaseModel):
    """
    Represents the result of a successful audio download.
    """
    audio_path: Path
    title: str
    url: str
    download_date: dt.date

def sanitize_filename(name: str) -> str:
    """
    Cleans a string to be a safe filename.
    - Replaces whitespace and dashes with underscores.
    - Converts to lowercase.
    - Removes special characters.
    """
    # Replace whitespace and dashes with underscores
    name = re.sub(r'[\s-]+', '_', name)
    # Convert to lowercase
    name = name.lower()
    # Remove special characters, keeping only alphanumerics and underscores
    name = re.sub(r'[^a-z0-9_]', '', name)
    return name

def download_audio(url: str) -> DownloadResult:
    """
    Downloads the audio from a given URL using yt-dlp.

    Args:
        url: The URL of the video to download.

    Returns:
        A DownloadResult object with metadata and the path to the downloaded audio.

    Raises:
        yt_dlp.utils.DownloadError: If yt-dlp fails to download the audio.
    """
    settings.temp_dir.mkdir(exist_ok=True)

    # Use yt-dlp to get video info without downloading
    ydl_opts_info = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'untitled')
        sanitized_title = sanitize_filename(title)

    # Define the output path
    date_str = dt.date.today().strftime('%Y%m%d')
    output_filename = f"{date_str}_{sanitized_title}.wav"
    output_path = settings.temp_dir / output_filename

    # Configure yt-dlp for audio download
    ydl_opts_download = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
        'outtmpl': str(output_path.with_suffix('')), # yt-dlp adds the extension
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        # Re-raise to be handled by the orchestrator
        raise e

    return DownloadResult(
        audio_path=output_path,
        title=title,
        url=url,
        download_date=dt.date.today()
    )
