import re
import datetime as dt
from pathlib import Path
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import yt_dlp

from video2mdnotes.config import settings
from video2mdnotes.logger import logger

class SourceInfo(BaseModel):
    """Metadata for one video, gathered without downloading any audio.

    Probing is split from fetching so the pipeline can decide whether audio is
    needed at all: when a usable human-authored caption track exists, the audio
    download and the Whisper run are both skipped.
    """
    title: str
    url: str
    tags: List[str] = []
    description: str = ""
    # Human-authored tracks. Machine `automatic_captions` are intentionally NOT
    # carried here — see core/captions.py for why they are not trusted.
    subtitles: Dict[str, List[Dict[str, Any]]] = {}
    has_automatic_captions: bool = False


class DownloadResult(BaseModel):
    """
    Represents the result of a successful audio download.
    """
    # None when the transcript came from captions and no audio was fetched.
    audio_path: Optional[Path] = None
    title: str
    url: str
    download_date: dt.date
    tags: List[str] = []
    description: str = ""

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

def probe_source(url: str) -> List[SourceInfo]:
    """
    Gathers metadata and caption availability WITHOUT downloading any audio.

    Split out from download_audio() so the caller can check for a usable caption
    track before paying for an audio download and a Whisper run.

    Args:
        url: The URL of the video or playlist to probe.

    Returns:
        A list of SourceInfo objects (one per video; playlists yield many).
    """
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

    sources: List[SourceInfo] = []
    for index, entry in enumerate(entries):
        # yt-dlp yields None for playlist items that are private, deleted or
        # geo-blocked. Skip them: one unavailable video in a long playlist must
        # not abort the whole run.
        if entry is None:
            logger.warning(f"Skipping unavailable playlist entry at position {index + 1}.")
            continue

        # For playlist entries, the 'url' key is present.
        # For a single video info dict, it might be missing. In that case, we use the original URL.
        sources.append(SourceInfo(
            # Prefer the canonical watch page. `url` on a YouTube entry is a
            # signed CDN link that expires, which made archived original_url.txt
            # files useless for re-running a source later.
            url=entry.get('webpage_url') or entry.get('url') or url,
            title=entry.get('title', 'untitled'),
            tags=entry.get('tags') or [],
            description=entry.get('description') or "",
            subtitles=entry.get('subtitles') or {},
            has_automatic_captions=bool(entry.get('automatic_captions')),
        ))
    return sources


def fetch_audio(source: SourceInfo) -> Path:
    """
    Downloads the audio for one probed source and returns the .wav path.

    Raises:
        yt_dlp.utils.DownloadError: If yt-dlp fails to download the audio.
    """
    settings.temp_dir.mkdir(exist_ok=True)

    sanitized_title = sanitize_filename(source.title)
    logger.info(f"Downloading audio: {source.title}")

    date_str = dt.date.today().strftime('%Y%m%d')
    output_path = settings.temp_dir / f"{date_str}_{sanitized_title}.wav"

    ydl_opts_download = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}],
        'outtmpl': str(output_path.with_suffix('')),
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download([source.url])
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Failed to download {source.title}. Reason: {e}")
        # Re-raise to stop the entire process if one video fails
        raise e

    return output_path


def download_audio(url: str) -> List[DownloadResult]:
    """
    Probes a URL and downloads audio for every video it yields.

    Retained as the unconditional download path (and for callers that always
    want audio). The captions-first pipeline uses probe_source() + fetch_audio()
    directly so it can skip this entirely.
    """
    results: List[DownloadResult] = []
    for source in probe_source(url):
        logger.info(f"Processing video: {source.title}")
        results.append(DownloadResult(
            audio_path=fetch_audio(source),
            title=source.title,
            url=source.url,
            download_date=dt.date.today(),
            tags=source.tags,
            description=source.description,
        ))
    return results
