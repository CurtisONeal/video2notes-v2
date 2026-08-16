from pathlib import Path

import pytest

from video2mdnotes.config import settings
from video2mdnotes.core.frames import Keyframe
from video2mdnotes.core.ranking import (
    dwell_times,
    parse_cue_phrases,
    score_frames,
    select_for_escalation,
)
from video2mdnotes.core.transcriber import Segment


def _frames(*timestamps):
    return [Keyframe(path=Path(f"f{i}.png"), timestamp=float(t))
            for i, t in enumerate(timestamps)]


# --- Dwell time: the strongest free signal ---

def test_dwell_is_gap_until_next_frame():
    assert dwell_times(_frames(0, 10, 40), video_duration=50)[:2] == [10.0, 30.0]


def test_final_frame_dwell_is_clamped():
    """A run truncated by FRAME_MAX must not credit its last frame with the
    entire unexamined remainder of the video.

    Measured regression: a 1120s video capped at 60 raw frames stopped
    extracting at 349s, and the final frame was handed a fabricated 771s dwell
    that scored 1.00 and squashed every other frame toward zero.
    """
    frames = _frames(0, 10, 20, 30)  # all observed gaps are 10s
    gaps = dwell_times(frames, video_duration=1120.0)
    assert gaps[-1] == pytest.approx(10.0 * settings.rank_final_dwell_clamp)
    assert gaps[-1] < 1090.0  # the un-clamped value


def test_single_frame_has_no_gap():
    assert dwell_times(_frames(5)) == [0.0]


def test_empty_input_is_safe():
    assert dwell_times([]) == []
    assert score_frames([]) == []


# --- Ranking beats chronological order ---

def test_long_dwell_outranks_transition_cluster():
    """The failure ranking exists to fix: chronological order spends the whole
    budget on a cluster of near-simultaneous transition frames."""
    frames = _frames(100, 101, 102, 103, 200)  # a 1s-apart cluster, then holds
    ranked = score_frames(frames, video_duration=300)
    # 103 is held for 97s and 200 closes the video; either may top the list.
    # What must never happen is a 1-second transition frame winning the budget.
    assert ranked[0].frame.timestamp in (103.0, 200.0)
    assert ranked[0].dwell_seconds >= 90.0


def test_flat_input_scores_neutral_not_zero():
    """Evenly spaced identical frames carry no signal — no opinion either."""
    ranked = score_frames(_frames(0, 10, 20), video_duration=30)
    assert all(0.0 <= s.score <= 1.0 for s in ranked)


# --- Audio cues ---

def test_audio_cue_near_frame_raises_its_score():
    frames = _frames(10, 100)
    segments = [Segment(start=98.0, end=101.0, text="as you can see here in this diagram")]
    ranked = score_frames(frames, segments=segments, video_duration=200)
    by_ts = {s.frame.timestamp: s for s in ranked}
    assert by_ts[100.0].audio_cue_score == 1.0
    assert by_ts[10.0].audio_cue_score == 0.0


def test_audio_cue_outside_window_does_not_count():
    frames = _frames(10)
    far = [Segment(start=500.0, end=502.0, text="as you can see")]
    assert score_frames(frames, segments=far, video_duration=600)[0].audio_cue_score == 0.0


def test_no_transcript_is_not_an_error():
    """Silent video is exactly why cues rank rather than trigger."""
    assert score_frames(_frames(0, 10), segments=None)[0].audio_cue_score == 0.0


def test_parse_cue_phrases_normalizes():
    assert parse_cue_phrases(" As You Can See , look at ") == ["as you can see", "look at"]


# --- Budget selection ---

def test_selection_never_escalates_an_ineligible_frame():
    """Ranking reorders what the gate allowed; it must not widen the gate."""
    frames = _frames(0, 10, 20)
    chosen = select_for_escalation(frames, [False, True, False], budget=3)
    assert chosen == {frames[1].path}


def test_selection_respects_budget():
    frames = _frames(0, 10, 20, 30, 40)
    chosen = select_for_escalation(frames, [True] * 5, budget=2, video_duration=60)
    assert len(chosen) == 2


def test_zero_budget_spends_nothing():
    frames = _frames(0, 10)
    assert select_for_escalation(frames, [True, True], budget=0) == set()


def test_all_eligible_within_budget_selects_all():
    frames = _frames(0, 10)
    assert select_for_escalation(frames, [True, True], budget=5) == {f.path for f in frames}
