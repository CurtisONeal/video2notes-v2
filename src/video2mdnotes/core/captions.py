"""Captions-first transcript sourcing.

When a source already ships a human-authored transcript, downloading the audio
and running ~10 minutes of Whisper over it is wasted work. This module turns an
existing caption track into the same `TranscriptResult` the transcriber
produces, so the rest of the pipeline is unchanged.

Two deliberate restrictions:

* **Manual tracks only.** yt-dlp separates human-authored `subtitles` from
  machine `automatic_captions`. Auto-captions are ASR *without* the vocabulary
  hint `build_initial_prompt()` supplies, so taking them would reintroduce the
  exact error class that hint was added to fix (e.g. "Claude" -> "Cloud"). They
  are also silently machine-translated: a probe of one English video listed
  `ab` (Abkhazian) among its automatic captions. Whisper is the better fallback.

* **A caption track must prove it carries speech.** Music videos return cues
  that are entirely `[♪♪♪]` / `[Music]`. Those pass a naive "are there segments"
  check and would feed the summarizer garbage it is obliged to summarize, so a
  track that fails `has_usable_speech()` is rejected and Whisper runs instead.
"""

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from video2mdnotes.config import settings
from video2mdnotes.logger import logger
from video2mdnotes.core.downloader import sanitize_filename
from video2mdnotes.core.webfetch import fetch_text
from video2mdnotes.core.transcriber import Segment, TranscriptResult, generate_markdown

# json3 first: it carries explicit start/duration per cue and needs no timestamp
# parsing. srt/vtt are the fallback for extractors that do not offer json3.
FORMAT_PREFERENCE = ("json3", "srt", "vtt")

# Cues that are pure sound description, not speech.
_NON_SPEECH_CUE = re.compile(r"^\s*[\[\(♪][^\]\)]*[\]\)♪]?\s*$")

# Japanese, Chinese and Korean are not space-delimited, so counting "words" the
# Latin way scores real speech as zero. CJK characters are therefore counted
# separately and converted to word-equivalents. Japanese averages roughly two
# characters per morpheme, so 2 is a deliberately conservative divisor — it
# under-counts rather than letting a junk track through.
_CJK_CHAR = re.compile(
    r"[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯ｦ-ﾟ]"
)
_CJK_CHARS_PER_WORD = 2

# Any run of 2+ unicode letters. Covers Latin, Cyrillic, Greek, Arabic, Hebrew
# and Devanagari, which are all space-delimited. CJK is stripped before this
# runs, or an entire unspaced sentence would score as a single "word".
_WORD = re.compile(r"[^\W\d_]{2,}", re.UNICODE)

# Hard cap so an oversized or hostile response cannot exhaust memory. The
# http/https restriction lives in core/webfetch.py, shared with embed scraping.
_MAX_CAPTION_BYTES = 8 * 1024 * 1024


def parse_lang_preference(raw: str) -> List[str]:
    """Parse a comma-separated language preference into an ordered list.

    "en,ja" tries English then Japanese. The token "any" matches whatever manual
    track the source happens to ship, which is what you want for content in a
    language you did not anticipate (e.g. Japanese instruction on an otherwise
    English-configured install).
    """
    return [part.strip().lower() for part in (raw or "").split(",") if part.strip()]


def select_track(
    subtitles: Dict[str, List[Dict[str, Any]]], langs: List[str]
) -> Optional[tuple[str, Dict[str, Any]]]:
    """Pick a caption track matching the language preference, cleanest format first.

    Preferences are tried in order. Each matches on language prefix, so "en"
    accepts "en-US"/"en-GB", with an exact match beating a regional variant.
    The token "any" accepts whatever manual track exists.

    Returns (matched_lang, format_dict), or None when nothing matches.
    """
    if not subtitles:
        return None

    for want in langs:
        if not want or want == "auto":
            continue

        if want == "any":
            candidates = list(subtitles)
        else:
            exact = [code for code in subtitles if code.lower() == want]
            prefixed = [
                code for code in subtitles if code.lower().split("-")[0] == want
            ]
            candidates = exact + [c for c in prefixed if c not in exact]

        for code in candidates:
            formats = subtitles.get(code) or []
            for ext in FORMAT_PREFERENCE:
                for fmt in formats:
                    if fmt.get("ext") == ext and fmt.get("url"):
                        return code, fmt
    return None


def count_speech_units(text: str) -> int:
    """Approximate word count that works for both spaced and CJK scripts."""
    cjk_chars = len(_CJK_CHAR.findall(text))
    # Remove CJK before word-matching so an unspaced sentence is not one "word".
    spaced = _CJK_CHAR.sub(" ", text)
    return len(_WORD.findall(spaced)) + cjk_chars // _CJK_CHARS_PER_WORD


def has_usable_speech(segments: List[Segment], min_words: int = 20) -> bool:
    """True when the track carries real speech rather than sound descriptions."""
    units = 0
    for seg in segments:
        text = seg.text.strip()
        if not text or _NON_SPEECH_CUE.match(text):
            continue
        units += count_speech_units(text)
    return units >= min_words


def parse_json3(raw: str) -> List[Segment]:
    """Parse YouTube's json3 caption format into segments."""
    data = json.loads(raw)
    segments: List[Segment] = []
    for event in data.get("events") or []:
        segs = event.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text:
            continue
        start = (event.get("tStartMs") or 0) / 1000.0
        duration = (event.get("dDurationMs") or 0) / 1000.0
        segments.append(Segment(start=start, end=start + duration, text=text))
    return segments


def _parse_timestamp(value: str) -> float:
    """Parse an SRT/VTT timestamp (HH:MM:SS,mmm or MM:SS.mmm) into seconds."""
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


def parse_srt_vtt(raw: str) -> List[Segment]:
    """Parse SRT or WebVTT cues into segments.

    Consecutive duplicate cues are dropped: VTT rolling-window captions repeat
    each line as new text is appended, which would otherwise trip the word count
    and inflate the transcript.
    """
    segments: List[Segment] = []
    pattern = re.compile(
        r"(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3})"
    )

    blocks = re.split(r"\n\s*\n", raw.replace("\r\n", "\n"))
    for block in blocks:
        match = pattern.search(block)
        if not match:
            continue
        body_lines = []
        for line in block.split("\n"):
            if pattern.search(line) or line.strip().isdigit():
                continue
            if line.strip().upper().startswith(("WEBVTT", "NOTE", "KIND:", "LANGUAGE:")):
                continue
            # Strip VTT inline karaoke/positioning tags.
            body_lines.append(re.sub(r"<[^>]+>", "", line).strip())

        text = " ".join(part for part in body_lines if part).strip()
        if not text:
            continue
        if segments and segments[-1].text == text:
            continue
        segments.append(
            Segment(
                start=_parse_timestamp(match.group(1)),
                end=_parse_timestamp(match.group(2)),
                text=text,
            )
        )
    return segments


def _fetch(url: str) -> str:
    """Fetch a caption track. Scheme and size restrictions live in webfetch."""
    return fetch_text(url, max_bytes=_MAX_CAPTION_BYTES)


def transcript_from_captions(
    title: str,
    subtitles: Dict[str, List[Dict[str, Any]]],
    lang: Optional[str] = None,
) -> Optional[TranscriptResult]:
    """Build a TranscriptResult from a human-authored caption track.

    Returns None whenever captions cannot be used, which is always a signal to
    fall back to Whisper — never an error. Only `subtitles` (manual tracks) may
    be passed here; `automatic_captions` are deliberately not accepted.
    """
    # Explicit arg > CAPTIONS_LANG > FW_LANG. Keeping CAPTIONS_LANG separate
    # matters for mixed-language libraries: FW_LANG tells Whisper what to expect,
    # but a Japanese-language source may still be worth taking captions from on
    # an otherwise English install.
    preference = parse_lang_preference(
        lang or settings.captions_lang or settings.fw_lang
    )
    selected = select_track(subtitles, preference)
    if not selected:
        return None

    code, fmt = selected
    try:
        raw = _fetch(fmt["url"])
        segments = (
            parse_json3(raw) if fmt.get("ext") == "json3" else parse_srt_vtt(raw)
        )
    except Exception as e:  # noqa: BLE001 - any failure just means "use Whisper"
        logger.warning(f"Caption track ({code}/{fmt.get('ext')}) unusable: {e}")
        return None

    if not has_usable_speech(segments, settings.captions_min_words):
        logger.info(
            f"Caption track {code} has too little speech to trust "
            f"({len(segments)} cues, under {settings.captions_min_words} "
            f"word-equivalents — typically music or sound-description only) "
            f"— falling back to Whisper."
        )
        return None

    provenance = f"captions (manual, {code})"
    # Sanitize: a title containing "/" (common — e.g. 'Aikido ... / Yamada
    # Sensei') would otherwise make Path treat it as a directory, and `.name`
    # would silently record only the trailing fragment as the source.
    source_file = Path(f"{sanitize_filename(title)}.{code}.{fmt.get('ext', 'captions')}")
    full_text = " ".join(seg.text for seg in segments)

    markdown = generate_markdown(
        title=title,
        source_file=source_file.name,
        segments=segments,
        language=code,
        model="none (human-authored captions)",
        transcript_source=provenance,
    )

    logger.success(
        f"Using human-authored captions ({code}/{fmt.get('ext')}, "
        f"{len(segments)} cues) — skipping audio download and Whisper."
    )

    return TranscriptResult(
        source_file=source_file,
        language=code,
        segments=segments,
        full_text=full_text,
        markdown_content=markdown,
        model_name="none (human-authored captions)",
        generated_at=dt.datetime.now(),
        transcript_source=provenance,
    )
