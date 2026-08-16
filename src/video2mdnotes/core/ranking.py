"""Deciding which keyframes are worth paying a vision model to look at.

The escalation gate (`needs_vision_model`) answers *eligibility* — could a
vision model add anything this frame's OCR did not? This module answers
*priority*: given a budget of N paid frames and more eligible frames than that,
which N actually matter?

Without ranking, the budget takes the first N in chronological order, so a
40-frame video with a 15-frame budget spends everything on the first third and
never sees the conclusion. That is a worse failure than it looks: intros and
title cards cluster at the start.

Every signal here is free — computed from data the pipeline already has:

* **Dwell time** — how long a frame stayed on screen before the next scene
  change. The single strongest signal available, and it costs nothing: a slide
  held for 90 seconds is deliberate content; a frame that flashes for one second
  is a transition. It is also what rescues the naive reading of "no text = a
  picture", since blank transition frames have no text *and* no dwell.
* **Uniqueness** — perceptual-hash distance to the other kept frames. A frame
  unlike anything else in the video carries information the others do not.
* **Audio cues** — the speaker saying "as you can see here" near a frame's
  timestamp is a direct statement that the visual matters. This only works when
  there is narration, which is exactly why it is a ranking signal rather than a
  trigger.
"""

import re
from typing import List, Optional, Sequence

from pydantic import BaseModel

from video2mdnotes.config import settings
from video2mdnotes.core.frames import Keyframe
from video2mdnotes.core.transcriber import Segment


class ScoredFrame(BaseModel):
    """A keyframe with its priority score and the components behind it."""
    frame: Keyframe
    score: float
    dwell_seconds: float
    dwell_score: float
    uniqueness_score: float
    audio_cue_score: float

    @property
    def why(self) -> str:
        """Short human-readable breakdown, for logs and debugging."""
        return (
            f"dwell={self.dwell_seconds:.0f}s({self.dwell_score:.2f}) "
            f"uniq={self.uniqueness_score:.2f} cue={self.audio_cue_score:.2f}"
        )


def parse_cue_phrases(raw: str) -> List[str]:
    return [p.strip().lower() for p in (raw or "").split(",") if p.strip()]


def dwell_times(frames: Sequence[Keyframe], video_duration: Optional[float] = None) -> List[float]:
    """Seconds each frame remained on screen, i.e. until the next scene change.

    The final frame runs to `video_duration` when known; otherwise it inherits
    the median of the others rather than an arbitrary constant, so it is neither
    unfairly favoured nor penalised.
    """
    if not frames:
        return []

    gaps: List[float] = []
    for i, frame in enumerate(frames[:-1]):
        gaps.append(max(0.0, frames[i + 1].timestamp - frame.timestamp))

    if not gaps:
        return [0.0]

    ordered = sorted(gaps)
    median = ordered[len(ordered) // 2]
    longest = ordered[-1]

    if video_duration is not None and video_duration > frames[-1].timestamp:
        final = video_duration - frames[-1].timestamp
    else:
        final = median

    # Clamp the final frame's dwell to the longest gap actually observed. When
    # FRAME_MAX truncates extraction, the last keyframe is not the last scene —
    # it is just where we stopped looking, and crediting it with every remaining
    # second of the video invents a dwell it never had. Measured: a 1120s video
    # capped at 60 raw frames stopped at 349s, handing its final frame a
    # fabricated 771s dwell that scored 1.00 and flattened every other score.
    #
    # Clamping to the longest observed gap rather than a multiple of the median
    # matters on transition-heavy content: there the median gap is ~1s, so a
    # median-based clamp would crush a genuinely held closing slide too.
    gaps.append(min(final, longest * settings.rank_final_dwell_clamp))
    return gaps


def _normalize(values: Sequence[float]) -> List[float]:
    """Scale to 0..1. All-equal input scores a flat 0.5 — no signal, no opinion."""
    if not values:
        return []
    low, high = min(values), max(values)
    if high - low < 1e-9:
        return [0.5] * len(values)
    return [(v - low) / (high - low) for v in values]


def _uniqueness(frames: Sequence[Keyframe]) -> List[float]:
    """Distance from each frame to its nearest neighbour, perceptually.

    Returns a flat neutral score when hashing is unavailable, so a missing
    optional dependency degrades the ranking rather than breaking it.
    """
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        return [0.5] * len(frames)

    hashes = []
    for frame in frames:
        try:
            with Image.open(frame.path) as image:
                hashes.append(imagehash.phash(image))
        except Exception:  # noqa: BLE001 - unreadable frame gets a neutral score
            hashes.append(None)

    distances: List[float] = []
    for i, digest in enumerate(hashes):
        if digest is None:
            distances.append(0.0)
            continue
        others = [abs(digest - other) for j, other in enumerate(hashes)
                  if other is not None and j != i]
        distances.append(float(min(others)) if others else 0.0)
    return _normalize(distances)


def _audio_cues(
    frames: Sequence[Keyframe],
    segments: Optional[Sequence[Segment]],
    phrases: Sequence[str],
    window: float,
) -> List[float]:
    """1.0 when a "look at this" phrase is spoken near the frame, else 0.0.

    Deliberately binary: the phrase either occurred nearby or it did not, and
    manufacturing a gradient from a keyword match would be false precision.
    """
    if not segments or not phrases:
        return [0.0] * len(frames)

    pattern = re.compile("|".join(re.escape(p) for p in phrases), re.IGNORECASE)
    cue_times = [
        seg.start for seg in segments if pattern.search(seg.text or "")
    ]
    if not cue_times:
        return [0.0] * len(frames)

    return [
        1.0 if any(abs(cue - frame.timestamp) <= window for cue in cue_times) else 0.0
        for frame in frames
    ]


def score_frames(
    frames: Sequence[Keyframe],
    segments: Optional[Sequence[Segment]] = None,
    video_duration: Optional[float] = None,
) -> List[ScoredFrame]:
    """Score frames by how much a vision model is likely to add, highest first."""
    if not frames:
        return []

    dwells = dwell_times(frames, video_duration)
    dwell_scores = _normalize(dwells)
    uniqueness = _uniqueness(frames)
    cues = _audio_cues(
        frames, segments,
        parse_cue_phrases(settings.rank_cue_phrases),
        settings.rank_cue_window,
    )

    total_weight = (
        settings.rank_weight_dwell
        + settings.rank_weight_uniqueness
        + settings.rank_weight_audio_cue
    ) or 1.0

    scored = [
        ScoredFrame(
            frame=frame,
            score=(
                settings.rank_weight_dwell * dwell_scores[i]
                + settings.rank_weight_uniqueness * uniqueness[i]
                + settings.rank_weight_audio_cue * cues[i]
            ) / total_weight,
            dwell_seconds=dwells[i],
            dwell_score=dwell_scores[i],
            uniqueness_score=uniqueness[i],
            audio_cue_score=cues[i],
        )
        for i, frame in enumerate(frames)
    ]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def select_for_escalation(
    frames: Sequence[Keyframe],
    eligible: Sequence[bool],
    budget: int,
    segments: Optional[Sequence[Segment]] = None,
    video_duration: Optional[float] = None,
) -> set:
    """Choose which frame paths get the paid vision call.

    `eligible` is the per-frame gate result — ranking only ever reorders frames
    that already qualify, it never escalates one the gate rejected.

    Returns a set of paths so the caller can keep emitting frames in
    chronological order while spending on the highest-scoring ones.
    """
    if budget <= 0:
        return set()

    candidates = [f for f, ok in zip(frames, eligible) if ok]
    if len(candidates) <= budget:
        return {f.path for f in candidates}

    ranked = score_frames(candidates, segments, video_duration)
    return {s.frame.path for s in ranked[:budget]}
