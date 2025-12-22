#!/usr/bin/env python3
import os
import sys
import argparse
import platform
# glob not needed; Path.glob is used instead
import datetime as dt
from pathlib import Path
from rich.progress import track

# Import faster_whisper with a helpful error if it's missing
try:
    from faster_whisper import WhisperModel
except Exception:
    print("ERROR: 'faster_whisper' is not importable in this Python environment.")
    print("Install it with: python -m pip install faster-whisper")
    print("See: https://github.com/guillaumekln/faster-whisper for more info.")
    raise

# ---------- SETTINGS ----------
# MODEL_NAME = os.getenv("FW_MODEL") or "medium"  # or "large-v3" - earlier version
# default to a small model for quicker tests
MODEL_NAME = os.getenv("FW_MODEL") or "tiny"
LANG = os.getenv("FW_LANG",  "en")
# Intel CPU: "int8_float16"; Apple Silicon CPU: "float16"
# Intel CPU: "int8" is safe; use "float32" if you want maximum compatibility
COMPUTE = os.getenv("FW_COMPUTE", "int8")
BEAM_SIZE = int(os.getenv("FW_BEAM", "1"))
VAD = os.getenv("FW_VAD", "true").lower() == "true"
CHUNK_SEC = int(os.getenv("FW_CHUNK", "30"))
# Make OUTDIR relative to the script's directory (project root) so outputs
# are always written to the repo's `transcripts/` folder regardless of cwd.
BASE_DIR = Path(__file__).resolve().parent
OUTDIR = BASE_DIR / Path(os.getenv("FW_OUTDIR", "transcripts"))
# --------------------------------


def print_env_info() -> None:
    """Print runtime configuration useful for debugging."""
    print("Python executable:", sys.executable)
    print("Python version:", sys.version.splitlines()[0])
    print(f"Project base dir: {BASE_DIR}")
    print(f"Output transcripts dir: {OUTDIR}")
    print(f"Whisper model: {MODEL_NAME}")
    print(f"Compute type: {COMPUTE}")
    print(f"VAD enabled: {VAD}")
    print("")


def detect_default_compute() -> str:
    """Auto-detect a sensible default compute type when not provided.

    Returns:
        A compute type string suitable for `faster_whisper` (e.g. 'float16', 'int8').
    """
    # Prefer float16 on Apple Silicon (arm64 macOS)
    try:
        sys_platform = platform.system()
        machine = platform.machine().lower()
    except Exception:
        return "int8"

    if sys_platform == "Darwin" and machine.startswith("arm"):
        return "float16"

    # For other systems, default to int8 for better CPU performance and smaller memory
    return "int8"


def ts(secs: float) -> str:
    s = int(secs)
    ms = int((secs - s) * 1000)
    return str(dt.timedelta(seconds=s)) + f".{ms:03d}"


def to_md(title: str, url_or_file: str, segments, language: str) -> str:
    lines = []
    lines.append("---")
    lines.append(f'title: "{title}"')
    lines.append(f"source: {url_or_file}")
    lines.append(f"model: {MODEL_NAME}")
    lines.append(f"language: {language}")
    lines.append(
        f"generated_at: {dt.datetime.now().isoformat(timespec='seconds')}")
    lines.append("---\n")
    lines.append("# Summary\n")
    lines.append("_(Write your 5-bullet summary here.)_\n")
    lines.append("# Notes\n")
    for seg in segments:
        start = ts(seg.start)
        text = seg.text.strip().replace("\n", " ")
        lines.append(f"- [{start}] {text}")
    lines.append("")
    return "\n".join(lines)


def main(word_timestamps: bool = False):
    """Transcribe all .wav files in the current directory."""
    # Print environment/config info for easier debugging
    print_env_info()
    # Ensure output and processed-wav directories exist
    OUTDIR.mkdir(exist_ok=True, parents=True)
    TRANS_WAV_DIR = BASE_DIR / "transcribed_wav"
    TRANS_WAV_DIR.mkdir(exist_ok=True, parents=True)

    # Find .wav files in the project directory (BASE_DIR)
    wav_paths = sorted(BASE_DIR.glob("*.wav"))
    if not wav_paths:
        print(f"No .wav files found in {BASE_DIR}")
        return

    print(f"Loading model: {MODEL_NAME} (compute_type={COMPUTE})")
    model = WhisperModel(MODEL_NAME, device="cpu", compute_type=COMPUTE)

    for wav_path in track(wav_paths, description="Transcribing"):
        base = wav_path.stem
        md_path = OUTDIR / f"{base}.md"
        if md_path.exists():
            # transcript already exists; skip
            continue
        print(f"Processing audio: {wav_path.name}")
        try:
            segments, info = model.transcribe(
                str(wav_path),
                language=LANG,
                vad_filter=VAD,
                beam_size=BEAM_SIZE,
                # Note: as of faster-whisper >=1.0.0 the argument is chunk_length.
                chunk_length=CHUNK_SEC,
                word_timestamps=word_timestamps,
            )
        except KeyboardInterrupt:
            print("Transcription interrupted by user. Exiting gracefully.")
            return

        segs = list(segments)
        doc = to_md(base, str(wav_path.name), segs, info.language or LANG)
        md_path.write_text(doc, encoding="utf-8")

        # Move processed wav into the transcribed_wav directory so it
        # is not picked up again on subsequent runs.
        try:
            dest = TRANS_WAV_DIR / wav_path.name
            wav_path.rename(dest)
        except Exception:
            # if move fails, continue without stopping
            pass

    print(f"Done. Markdown files in: {OUTDIR.resolve()}")


if __name__ == "__main__":
    # Allow override from env var if desired
    wt_env = os.getenv("FW_WORD_TIMESTAMPS", "false").lower()
    word_ts = wt_env in ("1", "true", "yes", "on")

    parser = argparse.ArgumentParser(
        description="Transcribe all .wav files in the project folder to Markdown using faster-whisper."
    )
    parser.add_argument(
        "--model_size",
        dest="model_size",
        help="Model size to use (e.g. tiny, small, medium, large-v3). Overrides FW_MODEL env var.",
    )
    parser.add_argument(
        "--compute",
        dest="compute",
        help="Compute type to use (e.g. float16, int8, int8_float16, float32). Overrides FW_COMPUTE env var.",
    )
    parser.add_argument(
        "--word-timestamps",
        dest="word_timestamps",
        action="store_true",
        help="Enable word-level timestamps (overrides FW_WORD_TIMESTAMPS).",
    )

    args = parser.parse_args()

    # Apply CLI overrides (fall back to env vars / defaults)
    MODEL_NAME = args.model_size or os.getenv("FW_MODEL") or MODEL_NAME
    # If compute not provided, try to detect a safe default
    COMPUTE = args.compute or os.getenv("FW_COMPUTE") or detect_default_compute()

    # Allow CLI word-timestamps flag to override env var
    if args.word_timestamps:
        word_ts = True

    try:
        main(word_timestamps=word_ts)
    except KeyboardInterrupt:
        print("Interrupted by user (KeyboardInterrupt). Exiting.")
        sys.exit(1)
