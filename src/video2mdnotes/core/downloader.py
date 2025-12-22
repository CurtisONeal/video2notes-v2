import re
import datetime as dt
from pathlib import Path
from pydantic import BaseModel
from typing import List
import yt_dlp

from video2mdnotes.config import settings
from video2mdnotes.logger import logger

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
    name = re.sub(r'[\s-]+', '_', name)
    name = name.lower()
    name = re.sub(r'[^a-z0-9_]', '', name)
    return name

def download_audio(url: str) -> List[DownloadResult]:
    """
    Downloads the audio from a given URL, handling both single videos and playlists.

    Args:
        url: The URL of the video or playlist to download.

    Returns:
        A list of DownloadResult objects.

    Raises:
        yt_dlp.utils.DownloadError: If yt-dlp fails to download the audio.
    """
    settings.temp_dir.mkdir(exist_ok=True)
    results: List[DownloadResult] = []

    # Adding extractor_args to mimic an Android client, which can be more reliable for playlists.
    ydl_opts_info = {
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        info = ydl.extract_info(url, download=False)

    # Determine if the result is a playlist or a single video
    if 'entries' in info:
        entries = info['entries']
    else:
        # It's a single video, wrap it in a list to use the same loop
        entries = [info]

    for entry in entries:
        # For playlist entries, the 'url' key is present.
        # For a single video info dict, it might be missing. In that case, we use the original URL.
        video_url = entry.get('url') or url
        title = entry.get('title', 'untitled')
        sanitized_title = sanitize_filename(title)
        
        logger.info(f"Processing video: {title}")

        date_str = dt.date.today().strftime('%Y%m%d')
        output_filename = f"{date_str}_{sanitized_title}.wav"
        output_path = settings.temp_dir / output_filename

        ydl_opts_download = {
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}],
            'outtmpl': str(output_path.with_suffix('')),
            'quiet': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                ydl.download([video_url])
            
            results.append(DownloadResult(
                audio_path=output_path,
                title=title,
                url=video_url,
                download_date=dt.date.today()
            ))
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Failed to download {title}. Reason: {e}")
            # Re-raise to stop the entire process if one video fails
            raise e
    
    return results
