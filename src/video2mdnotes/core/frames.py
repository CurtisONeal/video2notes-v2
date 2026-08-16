"""Keyframe extraction for videos whose information is on screen, not in audio.

Some instructional content carries its substance visually — slides, code
screencasts, tables, UI walkthroughs. The audio pipeline cannot see any of it,
and on a narration-free product video it correctly produces "No speech
detected" while the actual content sits in the pixels.

The enabling trick here is **scene-change detection rather than interval
sampling**. ffmpeg's `select='gt(scene,N)'` emits a frame only when the picture
materially changes, which on slide decks and screencasts maps almost one-to-one
onto "a new state appeared". That turns "look at 40 minutes of video" into
"look at ~30 distinct images", which is what makes the downstream OCR/VLM step
affordable at all.
"""

import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from video2mdnotes.config import settings
from video2mdnotes.logger import logger


class Keyframe(BaseModel):
    """One extracted frame, with its position in the video."""
    path: Path
    timestamp: float  # seconds into the video

    @property
    def label(self) -> str:
        """Human/filename-friendly position, e.g. '3m07s'."""
        return f"{int(self.timestamp) // 60}m{int(self.timestamp) % 60:02d}s"


# ffmpeg writes `pts_time:12.345` lines to stderr for each selected frame when
# the showinfo filter is attached. That is how we recover timestamps — the
# output filenames are just a sequence.
_PTS = re.compile(r"pts_time:([0-9.]+)")


def _ffmpeg() -> str:
    return shutil.which(settings.ffmpeg_path) or settings.ffmpeg_path


def extract_keyframes(
    video_path: Path,
    output_dir: Path,
    scene_threshold: Optional[float] = None,
    max_frames: Optional[int] = None,
) -> List[Keyframe]:
    """Extract frames where the picture materially changes.

    Returns frames in chronological order, capped at `max_frames`. An empty
    list is a normal outcome (a talking-head video has no slide changes) and
    should be treated as "nothing visual to extract", not an error.
    """
    threshold = scene_threshold if scene_threshold is not None else settings.frame_scene_threshold
    cap = max_frames if max_frames is not None else settings.frame_max

    output_dir.mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        [
            _ffmpeg(), "-i", str(video_path),
            "-vf", f"select='gt(scene,{threshold})',showinfo",
            "-vsync", "vfr",
            "-frames:v", str(cap),
            str(output_dir / "frame_%04d.png"),
        ],
        capture_output=True, text=True, timeout=settings.frame_extract_timeout,
    )

    # ffmpeg exits non-zero on some inputs even after writing frames, so trust
    # the files on disk over the return code.
    files = sorted(output_dir.glob("frame_*.png"))
    timestamps = [float(m) for m in _PTS.findall(proc.stderr or "")]

    if not files:
        if proc.returncode != 0:
            logger.warning(
                f"Frame extraction failed for {video_path.name}: "
                f"{(proc.stderr or '').strip()[-200:]}"
            )
        return []

    frames = [
        Keyframe(path=path, timestamp=timestamps[i] if i < len(timestamps) else 0.0)
        for i, path in enumerate(files)
    ]
    logger.success(f"Extracted {len(frames)} keyframe(s) from {video_path.name}")
    return frames


def deduplicate(frames: List[Keyframe], hamming_threshold: Optional[int] = None) -> List[Keyframe]:
    """Drop frames that are perceptually near-identical to one already kept.

    Scene detection over-fires on screencasts: a moving cursor, a blinking
    caret, or a line of typing all register as scene changes while the slide is
    unchanged. Comparing against every kept frame (not just the previous one)
    also collapses the common "flip back to the earlier diagram" pattern.
    """
    threshold = hamming_threshold if hamming_threshold is not None else settings.frame_dedupe_threshold
    if threshold <= 0 or len(frames) < 2:
        return frames

    try:
        import imagehash
        from PIL import Image
    except ImportError:
        logger.warning("imagehash/Pillow not installed — skipping frame de-duplication.")
        return frames

    kept: List[Keyframe] = []
    hashes: List["imagehash.ImageHash"] = []
    for frame in frames:
        try:
            with Image.open(frame.path) as image:
                digest = imagehash.phash(image)
        except Exception as e:  # noqa: BLE001 - an unreadable frame is not fatal
            logger.warning(f"Could not hash {frame.path.name}: {e}")
            kept.append(frame)
            continue

        if any(digest - seen <= threshold for seen in hashes):
            frame.path.unlink(missing_ok=True)
            continue
        hashes.append(digest)
        kept.append(frame)

    if len(kept) < len(frames):
        logger.info(f"De-duplicated {len(frames)} keyframe(s) down to {len(kept)}.")
    return kept


def extract_and_dedupe(video_path: Path, output_dir: Path) -> List[Keyframe]:
    """Scene-detect then de-duplicate, the normal entry point."""
    return deduplicate(extract_keyframes(video_path, output_dir))


def probe_has_video_stream(video_path: Path) -> bool:
    """True when the file actually carries a video stream worth sampling.

    The pipeline downloads audio-only .wav for the Whisper path; asking ffmpeg
    to scene-detect one wastes a subprocess and logs a confusing error.
    """
    proc = subprocess.run(
        [_ffmpeg(), "-i", str(video_path)],
        capture_output=True, text=True, timeout=60,
    )
    return "Video:" in (proc.stderr or "")


def download_video(url: str, dest_dir: Path) -> Optional[Path]:
    """Fetch a low-resolution video stream for frame extraction.

    Deliberately small: frames get downscaled before OCR/VLM anyway, so paying
    for a 1080p download to sample 30 stills is waste. Returns None on failure —
    visual extraction is an enhancement, never a reason to fail a run.
    """
    import yt_dlp

    dest_dir.mkdir(parents=True, exist_ok=True)
    output = dest_dir / "source_video.%(ext)s"
    opts = {
        "format": f"bestvideo[height<={settings.frame_video_height}]/best[height<={settings.frame_video_height}]/best",
        "outtmpl": str(output),
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:  # noqa: BLE001 - optional feature, never fatal
        logger.warning(f"Could not download video for frame extraction: {e}")
        return None

    for candidate in sorted(dest_dir.glob("source_video.*")):
        return candidate
    return None
