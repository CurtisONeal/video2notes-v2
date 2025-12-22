import datetime as dt
from pathlib import Path
from typing import List
from pydantic import BaseModel
from faster_whisper import WhisperModel
from rich.progress import Progress, SpinnerColumn, TextColumn

from video2mdnotes.config import settings

class Segment(BaseModel):
    """Represents a single segment of transcribed text."""
    start: float
    end: float
    text: str

class TranscriptResult(BaseModel):
    """Represents the full transcription result."""
    source_file: Path
    language: str
    segments: List[Segment]
    full_text: str
    markdown_content: str
    model_name: str
    generated_at: dt.datetime

def format_timestamp(seconds: float) -> str:
    """Formats seconds into HH:MM:SS.mmm string."""
    s = int(seconds)
    ms = int((seconds - s) * 1000)
    return f"{str(dt.timedelta(seconds=s))}.{ms:03d}"

def generate_markdown(title: str, source_file: str, segments: List[Segment], language: str, model: str) -> str:
    """Generates the Markdown formatted transcript."""
    lines = []
    lines.append("---")
    lines.append(f'title: "{title}"')
    lines.append(f"source: {source_file}")
    lines.append(f"model: {model}")
    lines.append(f"language: {language}")
    lines.append(f"generated_at: {dt.datetime.now().isoformat(timespec='seconds')}")
    lines.append("---\n")
    lines.append("# Summary\n")
    lines.append("_(Write your 5-bullet summary here.)_\n")
    lines.append("# Notes\n")
    
    for seg in segments:
        start = format_timestamp(seg.start)
        text = seg.text.strip().replace("\n", " ")
        lines.append(f"- [{start}] {text}")
    
    lines.append("")
    return "\n".join(lines)

def transcribe_audio(audio_path: Path, title: str = "Unknown") -> TranscriptResult:
    """
    Transcribes the given audio file using faster-whisper.

    Args:
        audio_path: Path to the .wav file.
        title: Title of the video (for the markdown header).

    Returns:
        TranscriptResult object containing the transcript and metadata.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Load Model
    # We use a spinner here because loading the model can take a few seconds
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Loading Whisper model ({settings.fw_model})...", total=None)
        
        model = WhisperModel(
            settings.fw_model,
            device="cpu", # Force CPU for now as per requirements (can be config'd later)
            compute_type=settings.fw_compute
        )

    # Transcribe
    # Note: faster-whisper returns a generator, so the transcription happens as we iterate
    segments_generator, info = model.transcribe(
        str(audio_path),
        language=settings.fw_lang if settings.fw_lang != "auto" else None,
        beam_size=1,
        vad_filter=True
    )

    segments_list: List[Segment] = []
    full_text_parts = []

    # We can't easily use a progress bar for the *duration* unless we know the audio length beforehand.
    # For simplicity in this version, we'll just iterate.
    # In a future version, we can use `pydub` or `ffprobe` to get duration and show a % bar.
    
    print(f"Transcribing {audio_path.name}...")
    
    for segment in segments_generator:
        seg_obj = Segment(
            start=segment.start,
            end=segment.end,
            text=segment.text
        )
        segments_list.append(seg_obj)
        full_text_parts.append(segment.text)

    full_text = "".join(full_text_parts)
    
    # Generate Markdown
    md_content = generate_markdown(
        title=title,
        source_file=audio_path.name,
        segments=segments_list,
        language=info.language,
        model=settings.fw_model
    )

    return TranscriptResult(
        source_file=audio_path,
        language=info.language,
        segments=segments_list,
        full_text=full_text,
        markdown_content=md_content,
        model_name=settings.fw_model,
        generated_at=dt.datetime.now()
    )
