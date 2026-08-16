"""Reading keyframes: local OCR first, a vision model only where OCR isn't enough.

Two tiers, because they have wildly different economics:

* **OCR** is free and local. On macOS the Vision framework is fast, good on code
  and UI, and costs nothing — so it runs on every keyframe unconditionally.
* **A vision model** is metered API spend, per image, and cannot use the
  subscription backend: `claude-cli` runs with `Read` disabled (the
  prompt-injection guard for untrusted source content), so images cannot be
  handed to it without reopening exactly that hole. Vision therefore escalates
  only for frames OCR cannot explain — diagrams, charts, plots, UI layouts,
  where reading the glyphs is not the same as understanding the picture.

That ordering is the whole cost story. Reading every frame with a frontier
model runs roughly $0.70-0.80 per video; OCR-first with selective escalation
usually lands in cents, because most slides *are* mostly text.
"""

import base64
import platform
import re
from pathlib import Path
from typing import List, Optional

import litellm
from pydantic import BaseModel

from video2mdnotes.config import settings
from video2mdnotes.logger import logger
from video2mdnotes.core.frames import Keyframe
from video2mdnotes.core.summarizer import _api_key_for

# A frame whose OCR yields at least this much real text is treated as
# self-explanatory. Below it, the picture is probably carrying the meaning.
_WORD = re.compile(r"[^\W\d_]{2,}", re.UNICODE)

VLM_PROMPT = (
    "This is a single frame from an instructional video. Describe only what is "
    "actually visible: the structure of any diagram, chart, table, or UI, and "
    "what it conveys. Do not speculate about parts of the video you cannot see, "
    "and do not invent labels or values that are not legible in the image. If "
    "the frame carries no meaningful information, reply exactly: NO CONTENT."
)


class FrameReading(BaseModel):
    """What was recovered from one keyframe, and how."""
    timestamp: float
    label: str
    image_path: Path
    ocr_text: str = ""
    description: str = ""
    # "ocr" | "ocr+vlm:<model>" | "none" — provenance, same discipline as
    # transcript_source: a machine reading and a model's interpretation are
    # different kinds of evidence and must stay distinguishable.
    source: str = "none"

    @property
    def is_empty(self) -> bool:
        return not (self.ocr_text.strip() or self.description.strip())


def ocr_available() -> bool:
    """True when local OCR can run on this machine."""
    if settings.ocr_backend == "none":
        return False
    if platform.system() != "Darwin":
        return False
    try:
        import ocrmac  # noqa: F401
        return True
    except ImportError:
        return False


def ocr_image(image_path: Path) -> str:
    """Read text from an image using the macOS Vision framework.

    Returns "" on any failure — a frame we cannot read is not an error, it just
    escalates to the vision tier (or is dropped).
    """
    try:
        from ocrmac import ocrmac as _ocrmac
        annotations = _ocrmac.OCR(str(image_path)).recognize()
    except Exception as e:  # noqa: BLE001 - OCR is best-effort by design
        logger.warning(f"OCR failed on {image_path.name}: {e}")
        return ""

    lines = []
    for annotation in annotations or []:
        # ocrmac yields (text, confidence, bbox)
        text = annotation[0] if isinstance(annotation, (tuple, list)) else str(annotation)
        confidence = annotation[1] if isinstance(annotation, (tuple, list)) and len(annotation) > 1 else 1.0
        if text and confidence >= settings.ocr_min_confidence:
            lines.append(str(text).strip())
    return "\n".join(line for line in lines if line)


def needs_vision_model(ocr_text: str) -> bool:
    """True when OCR alone probably didn't capture what the frame conveys.

    A slide that OCR'd into a paragraph of prose is already understood. A frame
    that yields a handful of axis labels is a chart, and the chart is the point.
    """
    return len(_WORD.findall(ocr_text)) < settings.vlm_escalate_below_words


def _encode(image_path: Path) -> tuple[str, str]:
    media_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    return media_type, base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")


def describe_image(image_path: Path, model: Optional[str] = None) -> str:
    """Ask a vision model what a frame shows. Returns "" if it declines or fails."""
    model = model or settings.vlm_model
    media_type, data = _encode(image_path)

    try:
        response = litellm.completion(
            model=model,
            # None lets litellm fall back to the provider's env var, which is
            # the usual setup when the repo .env still holds a placeholder.
            api_key=_api_key_for(model),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:{media_type};base64,{data}"}},
                    {"type": "text", "text": VLM_PROMPT},
                ],
            }],
            timeout=180,
        )
        text = (response.choices[0].message.content or "").strip()
    except Exception as e:  # noqa: BLE001 - visual enrichment is never fatal
        logger.warning(f"Vision model failed on {image_path.name}: {e}")
        return ""

    return "" if text.upper().startswith("NO CONTENT") else text


def read_frames(frames: List[Keyframe]) -> List[FrameReading]:
    """Run the OCR-then-escalate tier over extracted keyframes."""
    readings: List[FrameReading] = []
    have_ocr = ocr_available()
    if not have_ocr and settings.ocr_backend != "none":
        logger.warning(
            "Local OCR unavailable (macOS Vision only) — every frame will "
            "escalate to the vision model, which costs metered API spend. "
            "Set OCR_BACKEND=none or EXTRACT_FRAMES=false to avoid this."
        )

    escalated = 0
    for frame in frames:
        text = ocr_image(frame.path) if have_ocr else ""
        reading = FrameReading(
            timestamp=frame.timestamp,
            label=frame.label,
            image_path=frame.path,
            ocr_text=text,
            source="ocr" if text else "none",
        )

        if settings.vlm_enabled and needs_vision_model(text):
            if escalated >= settings.vlm_max_frames:
                logger.info(
                    f"Vision-model budget reached ({settings.vlm_max_frames} frames); "
                    f"remaining frames use OCR text only."
                )
            else:
                description = describe_image(frame.path)
                if description:
                    reading.description = description
                    reading.source = f"{reading.source}+vlm:{settings.vlm_model}".lstrip("+")
                    escalated += 1

        readings.append(reading)

    kept = [r for r in readings if not r.is_empty]
    logger.success(
        f"Read {len(kept)}/{len(frames)} keyframe(s) "
        f"({escalated} escalated to {settings.vlm_model})"
    )
    return kept


def render_markdown(readings: List[FrameReading], frames_dirname: str = "frames") -> str:
    """Render frame readings as a markdown section with embedded images.

    Image links are relative so the notes directory stays portable — moving or
    zipping the run directory keeps the images resolving.
    """
    if not readings:
        return ""

    lines = ["## Visual Content\n"]
    lines.append(
        "_Extracted from video keyframes. OCR text is a machine reading of what "
        "is on screen; descriptions are a vision model's interpretation._\n"
    )
    for reading in readings:
        lines.append(f"### [{reading.label}]\n")
        lines.append(f"![Frame at {reading.label}]({frames_dirname}/{reading.image_path.name})\n")
        if reading.ocr_text.strip():
            lines.append("**On screen:**\n")
            lines.append("```text")
            lines.append(reading.ocr_text.strip())
            lines.append("```\n")
        if reading.description.strip():
            lines.append(f"**Description:** {reading.description.strip()}\n")
        lines.append(f"_source: {reading.source}_\n")
    return "\n".join(lines)
