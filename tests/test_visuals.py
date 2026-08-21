from pathlib import Path
from unittest.mock import patch

import pytest

from video2mdnotes.config import settings
from video2mdnotes.core.frames import Keyframe
from video2mdnotes.core.summarizer import real_key
from video2mdnotes.core.visuals import (
    FrameReading,
    needs_vision_model,
    read_frames,
    render_markdown,
)


@pytest.fixture
def visual_settings():
    saved = (settings.vlm_enabled, settings.vlm_model,
             settings.vlm_escalate_below_words, settings.vlm_max_frames)
    yield settings
    (settings.vlm_enabled, settings.vlm_model,
     settings.vlm_escalate_below_words, settings.vlm_max_frames) = saved


# --- Escalation policy: this is what controls the bill ---

def test_text_heavy_frame_does_not_escalate(visual_settings):
    """A slide that OCR'd into prose is already understood — don't pay for it."""
    # A real prose slide, not a caption fragment: the threshold exists to
    # separate "the text IS the content" from "the picture is the content".
    prose = (
        "Gradient descent iteratively minimizes the loss function by stepping "
        "downhill along the negative gradient. The learning rate controls how "
        "large each step is."
    )
    assert needs_vision_model(prose) is False


@pytest.mark.parametrize("ocr", ["", "784", "OOO\nOO\n784", "→ 10\n• 00"])
def test_picture_carrying_frame_escalates(ocr, visual_settings):
    """Measured real output from a diagram-heavy explainer: OCR yields fragments."""
    assert needs_vision_model(ocr) is True


def test_escalation_respects_frame_budget(tmp_path, visual_settings):
    """One dense deck must not run away with the bill."""
    settings.vlm_enabled = True
    settings.vlm_max_frames = 2
    frames = []
    for i in range(5):
        p = tmp_path / f"frame_{i}.png"
        p.write_bytes(b"x")
        frames.append(Keyframe(path=p, timestamp=float(i)))

    with patch("video2mdnotes.core.visuals.ocr_available", return_value=True), \
         patch("video2mdnotes.core.visuals.ocr_image", return_value=""), \
         patch("video2mdnotes.core.visuals.describe_image", return_value="a chart") as vlm:
        read_frames(frames)

    assert vlm.call_count == 2


def test_vlm_disabled_never_calls_the_model(tmp_path, visual_settings):
    settings.vlm_enabled = False
    p = tmp_path / "f.png"
    p.write_bytes(b"x")

    with patch("video2mdnotes.core.visuals.ocr_available", return_value=True), \
         patch("video2mdnotes.core.visuals.ocr_image", return_value="some text"), \
         patch("video2mdnotes.core.visuals.describe_image") as vlm:
        read_frames([Keyframe(path=p, timestamp=0.0)])

    vlm.assert_not_called()


def test_empty_frames_are_dropped(tmp_path, visual_settings):
    """A frame yielding neither OCR text nor a description is not worth keeping."""
    settings.vlm_enabled = False
    p = tmp_path / "f.png"
    p.write_bytes(b"x")

    with patch("video2mdnotes.core.visuals.ocr_available", return_value=True), \
         patch("video2mdnotes.core.visuals.ocr_image", return_value=""):
        assert read_frames([Keyframe(path=p, timestamp=0.0)]) == []


# --- Provenance and rendering ---

def test_markdown_keeps_ocr_and_description_distinguishable():
    """A machine reading and a model's interpretation are different evidence."""
    reading = FrameReading(
        timestamp=42.0, label="0m42s", image_path=Path("frames/frame_0001.png"),
        ocr_text="784", description="A neural network diagram.",
        source="ocr+vlm:anthropic/claude-haiku-4-5",
    )
    md = render_markdown([reading])
    assert "**On screen:**" in md
    assert "**Description:**" in md
    assert "_source: ocr+vlm:anthropic/claude-haiku-4-5_" in md
    # Relative link so the run directory stays portable when moved or zipped.
    assert "](frames/frame_0001.png)" in md
    assert "[0m42s]" in md


def test_markdown_empty_when_nothing_read():
    assert render_markdown([]) == ""


# --- Placeholder key guard ---

@pytest.mark.parametrize("value", ["your_key_here", "", "   ", None, "sk-..."])
def test_placeholder_keys_resolve_to_none(value):
    """`.env.example` ships truthy placeholders that would reach the provider."""
    assert real_key(value) is None


def test_real_key_passes_through():
    assert real_key("sk-ant-real123") == "sk-ant-real123"


def test_keyframe_label_formats_position():
    assert Keyframe(path=Path("x.png"), timestamp=187.0).label == "3m07s"


# --- Visual section placement (shared by inline and visuals-only paths) ---

from video2mdnotes.core.visuals import (  # noqa: E402
    TRANSCRIPT_MARKER,
    has_usable_notes,
    insert_visual_section,
)
from video2mdnotes.core.summarizer import EMPTY_TRANSCRIPT_PLACEHOLDER  # noqa: E402

VISUALS = "## Visual Content\n\n![f](frames/a.png)\n"


def test_visuals_go_before_the_appended_transcript():
    out = insert_visual_section(f"Notes.{TRANSCRIPT_MARKER}raw", VISUALS)
    assert out.index("## Visual Content") < out.index("## Transcript")


def test_visuals_append_when_there_is_no_transcript():
    out = insert_visual_section("Notes.", VISUALS)
    assert out.endswith(VISUALS.rstrip()) or "## Visual Content" in out


def test_reinserting_replaces_rather_than_stacks():
    """A visuals-only pass must be re-runnable without duplicating sections."""
    once = insert_visual_section(f"Notes.{TRANSCRIPT_MARKER}raw", VISUALS)
    twice = insert_visual_section(once, "## Visual Content\n\n![g](frames/b.png)\n")
    assert twice.count("## Visual Content") == 1
    assert "b.png" in twice and "a.png" not in twice
    assert twice.index("## Visual Content") < twice.index("## Transcript")


def test_empty_visuals_leave_the_summary_untouched():
    base = f"Notes.{TRANSCRIPT_MARKER}raw"
    assert insert_visual_section(base, "") == base


# --- Empty-result detection (drives the no_summary_ prefix) ---

def test_placeholder_only_is_not_usable_notes():
    assert has_usable_notes(f"{EMPTY_TRANSCRIPT_PLACEHOLDER}{TRANSCRIPT_MARKER}") is False


def test_visuals_rescue_an_otherwise_empty_result():
    """The measured case: a silent product video whose content is all on screen."""
    text = insert_visual_section(
        f"{EMPTY_TRANSCRIPT_PLACEHOLDER}{TRANSCRIPT_MARKER}", VISUALS
    )
    assert has_usable_notes(text) is True


def test_real_summary_is_usable():
    assert has_usable_notes(f"## Summary\n- a real point{TRANSCRIPT_MARKER}raw") is True


# --- Download output selection (intermittent-failure regression) ---

def test_download_prefers_merged_output_over_fragments(tmp_path):
    """yt-dlp leaves per-stream fragments beside the merged file and deletes
    them after merging. Sorted-first picks the fragment ('f' < 'm'), which is
    gone by the time ffmpeg opens it — an intermittent "No such file" that
    retries cleanly and looks like flakiness."""
    from unittest.mock import patch
    from video2mdnotes.core.frames import download_video

    (tmp_path / "source_video.f399.mp4").write_bytes(b"x" * 10)
    (tmp_path / "source_video.mp4").write_bytes(b"x" * 500)

    class _FakeYDL:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def download(self, urls): return 0

    with patch("yt_dlp.YoutubeDL", _FakeYDL):
        got = download_video("https://example/v", tmp_path)

    assert got is not None and got.name == "source_video.mp4"
