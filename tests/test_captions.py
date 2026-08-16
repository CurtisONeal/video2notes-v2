import json
from unittest.mock import patch

import pytest

from video2mdnotes.core.captions import (
    _fetch,
    count_speech_units,
    has_usable_speech,
    parse_json3,
    parse_lang_preference,
    parse_srt_vtt,
    select_track,
    transcript_from_captions,
)
from video2mdnotes.core.transcriber import Segment


def _track(*exts):
    return [{"ext": e, "url": f"https://example.test/{e}"} for e in exts]


# --- Track selection ---

def test_select_track_prefers_json3():
    """json3 carries explicit start/duration, so it wins over srt/vtt."""
    subs = {"en": _track("vtt", "srt", "json3")}
    code, fmt = select_track(subs, ["en"])
    assert code == "en"
    assert fmt["ext"] == "json3"


def test_select_track_falls_back_when_no_json3():
    """Extractors that offer only srt/vtt still work."""
    subs = {"en": _track("vtt", "srt")}
    _, fmt = select_track(subs, ["en"])
    assert fmt["ext"] == "srt"


def test_select_track_matches_regional_variant():
    """A request for 'en' should accept 'en-US'."""
    subs = {"en-US": _track("json3")}
    code, _ = select_track(subs, ["en"])
    assert code == "en-US"


def test_select_track_prefers_exact_over_regional():
    subs = {"en-GB": _track("json3"), "en": _track("json3")}
    code, _ = select_track(subs, ["en"])
    assert code == "en"


def test_select_track_ignores_other_languages():
    subs = {"de": _track("json3"), "ja": _track("json3")}
    assert select_track(subs, ["en"]) is None


def test_select_track_returns_none_for_empty_or_auto():
    assert select_track({}, ["en"]) is None
    # "auto" language means we have no target to match — prefer Whisper.
    assert select_track({"en": _track("json3")}, ["auto"]) is None


def test_select_track_honours_preference_order():
    """'en,ja' takes English when both exist; 'ja,en' takes Japanese."""
    subs = {"en": _track("json3"), "ja": _track("json3")}
    assert select_track(subs, ["en", "ja"])[0] == "en"
    assert select_track(subs, ["ja", "en"])[0] == "ja"


def test_select_track_falls_through_to_second_preference():
    subs = {"ja": _track("json3")}
    assert select_track(subs, ["en", "ja"])[0] == "ja"


def test_select_track_any_accepts_whatever_exists():
    """'any' is how Japanese content is reachable on an English-configured install."""
    subs = {"ja": _track("json3")}
    assert select_track(subs, ["en", "any"])[0] == "ja"
    assert select_track({}, ["any"]) is None


def test_parse_lang_preference_splits_and_normalizes():
    assert parse_lang_preference(" EN , ja ") == ["en", "ja"]
    assert parse_lang_preference("") == []


# --- Parsing ---

def test_parse_json3_maps_start_and_duration():
    raw = json.dumps({"events": [
        {"tStartMs": 1360, "dDurationMs": 1680, "segs": [{"utf8": "Hello "}, {"utf8": "world"}]},
        {"tStartMs": 5000, "dDurationMs": 2000, "segs": [{"utf8": "Second cue"}]},
        {"tStartMs": 9000, "dDurationMs": 500},  # no segs -> skipped
    ]})
    segments = parse_json3(raw)
    assert len(segments) == 2
    assert segments[0].start == pytest.approx(1.36)
    assert segments[0].end == pytest.approx(3.04)
    assert segments[0].text == "Hello world"


def test_parse_srt_vtt_handles_srt_comma_timestamps():
    raw = (
        "1\n"
        "00:00:01,000 --> 00:00:03,500\n"
        "First line\n\n"
        "2\n"
        "00:00:04,000 --> 00:00:06,000\n"
        "Second line\n"
    )
    segments = parse_srt_vtt(raw)
    assert [s.text for s in segments] == ["First line", "Second line"]
    assert segments[0].start == pytest.approx(1.0)
    assert segments[0].end == pytest.approx(3.5)


def test_parse_srt_vtt_drops_rolling_window_duplicates():
    """VTT auto-caption style repeats each cue; duplicates must not stack up."""
    raw = (
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:03.000\n"
        "the same line\n\n"
        "00:00:03.000 --> 00:00:05.000\n"
        "the same line\n\n"
        "00:00:05.000 --> 00:00:07.000\n"
        "a new line\n"
    )
    segments = parse_srt_vtt(raw)
    assert [s.text for s in segments] == ["the same line", "a new line"]


def test_parse_srt_vtt_strips_inline_tags():
    raw = "00:00:01.000 --> 00:00:02.000\n<c.colorE5E5E5>tagged</c> text\n"
    assert parse_srt_vtt(raw)[0].text == "tagged text"


# --- Junk guard ---

def test_has_usable_speech_rejects_music_only_cues():
    """Real case: a music video's caption track is entirely sound description."""
    segments = [Segment(start=0, end=1, text=t) for t in
                ["[♪♪♪]", "[Music]", "(upbeat music)", "♪"]]
    assert has_usable_speech(segments) is False


REAL_DIALOGUE = (
    "Today we are launching a new model, and it is the most capable one we have "
    "released so far. It ships with safeguards that make it ready for general use "
    "across a wide range of everyday tasks."
)


def test_has_usable_speech_accepts_real_dialogue():
    assert has_usable_speech([Segment(start=0, end=5, text=REAL_DIALOGUE)]) is True


def test_has_usable_speech_counts_across_cues_ignoring_sound_tags():
    """Speech split over many cues still counts; interleaved [Music] does not."""
    words = "one two three four five six seven eight nine ten"
    segments = [Segment(start=0, end=1, text=words),
                Segment(start=1, end=2, text="[Music]"),
                Segment(start=2, end=3, text=words)]
    assert has_usable_speech(segments) is True


def test_has_usable_speech_rejects_sub_threshold_track():
    """A near-empty track falls back to Whisper by design.

    The cost of a false rejection is only a slower run, never a wrong summary,
    so the threshold errs toward re-transcribing.
    """
    assert has_usable_speech([Segment(start=0, end=1, text="Hi there everyone")]) is False


# --- End-to-end module behavior ---

def test_transcript_from_captions_builds_result_with_provenance():
    raw = json.dumps({"events": [
        {"tStartMs": 0, "dDurationMs": 3000, "segs": [{"utf8": REAL_DIALOGUE}]},
    ]})
    with patch("video2mdnotes.core.captions._fetch", return_value=raw):
        result = transcript_from_captions("My Video", {"en": _track("json3")}, lang="en")

    assert result is not None
    assert result.transcript_source == "captions (manual, en)"
    # Provenance must be visible in the file a human actually reads.
    assert "transcript_source: captions (manual, en)" in result.markdown_content
    # No Whisper model was involved; model_name must not imply one.
    assert "captions" in result.model_name


def test_transcript_from_captions_rejects_music_only_track():
    """A junk track must fall back to Whisper, not produce a bogus transcript."""
    raw = json.dumps({"events": [
        {"tStartMs": 0, "dDurationMs": 1000, "segs": [{"utf8": "[♪♪♪]"}]},
        {"tStartMs": 2000, "dDurationMs": 1000, "segs": [{"utf8": "[Music]"}]},
    ]})
    with patch("video2mdnotes.core.captions._fetch", return_value=raw):
        assert transcript_from_captions("Music Video", {"en": _track("json3")}, lang="en") is None


def test_transcript_from_captions_returns_none_on_fetch_failure():
    """A network failure means 'use Whisper', never an exception."""
    with patch("video2mdnotes.core.captions._fetch", side_effect=OSError("boom")):
        assert transcript_from_captions("V", {"en": _track("json3")}, lang="en") is None


def test_transcript_from_captions_returns_none_without_matching_track():
    assert transcript_from_captions("V", {"de": _track("json3")}, lang="en") is None
    assert transcript_from_captions("V", {}, lang="en") is None


# --- CJK support (Aikido material is frequently Japanese) ---

JAPANESE_SPEECH = (
    "今日は新しいモデルを発表します。これは私たちがこれまでに公開した中で"
    "最も高性能なモデルです。安全対策も備えていますので安心してお使いください。"
)
CHINESE_SPEECH = (
    "今天我们发布了一个新模型，这是我们迄今为止发布的最强大的模型，"
    "并且配备了完善的安全防护措施，可以放心使用。"
)


@pytest.mark.parametrize("text", [JAPANESE_SPEECH, CHINESE_SPEECH])
def test_has_usable_speech_accepts_cjk(text):
    """CJK is not space-delimited; counting Latin words scored real speech as 0."""
    assert has_usable_speech([Segment(start=0, end=9, text=text)]) is True


def test_cjk_music_cues_still_rejected():
    """The guard must not become a rubber stamp for CJK tracks."""
    segments = [Segment(start=0, end=1, text=t) for t in ["[音楽]", "♪", "[拍手]"]]
    assert has_usable_speech(segments) is False


def test_count_speech_units_does_not_treat_unspaced_cjk_as_one_word():
    assert count_speech_units(JAPANESE_SPEECH) > 20


def test_japanese_captions_end_to_end():
    raw = json.dumps({"events": [
        {"tStartMs": 0, "dDurationMs": 4000, "segs": [{"utf8": JAPANESE_SPEECH}]},
    ]})
    with patch("video2mdnotes.core.captions._fetch", return_value=raw):
        result = transcript_from_captions("合気道の稽古", {"ja": _track("json3")}, lang="ja")

    assert result is not None
    assert result.transcript_source == "captions (manual, ja)"


# --- Hardening ---

@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://host/x.vtt", "data:text/plain,hi"])
def test_fetch_refuses_non_http_schemes(url):
    """Caption URLs are third-party metadata; file:// would leak local files."""
    with pytest.raises(ValueError, match="scheme"):
        _fetch(url)


def test_fetch_rejects_oversized_response():
    """Oversized bodies must raise, not silently truncate into a partial transcript."""
    class _Resp:
        def read(self, n): return b"x" * n
        def __enter__(self): return self
        def __exit__(self, *a): return False

    with patch("video2mdnotes.core.webfetch.urllib.request.urlopen", return_value=_Resp()):
        with pytest.raises(ValueError, match="exceeds"):
            _fetch("https://example.test/huge.vtt")


def test_title_with_slash_does_not_truncate_recorded_source():
    """A real archived title: 'Intro to "Aikido..." / Yamada Sensei'."""
    raw = json.dumps({"events": [
        {"tStartMs": 0, "dDurationMs": 3000, "segs": [{"utf8": REAL_DIALOGUE}]},
    ]})
    title = 'Intro to "Aikido: The Power and the Basics 1" / Yamada Sensei'
    with patch("video2mdnotes.core.captions._fetch", return_value=raw):
        result = transcript_from_captions(title, {"en": _track("json3")}, lang="en")

    # No directory component, so `.name` cannot silently drop the leading title.
    assert len(result.source_file.parts) == 1
    assert "yamada" in result.source_file.name
    assert "aikido" in result.source_file.name
