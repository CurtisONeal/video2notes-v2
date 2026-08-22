import pytest

from video2mdnotes.config import settings
from video2mdnotes.core import profiles as P


class _Src:
    def __init__(self, **kw):
        for k in ("uploader", "channel", "url", "playlist_title", "title"):
            setattr(self, k, kw.get(k, ""))


@pytest.fixture
def clean_settings():
    keys = ("frame_scene_threshold", "frame_dedupe_threshold", "frame_max",
            "vlm_escalate_below_words", "vlm_max_frames", "extract_frames",
            "profile_source_map")
    saved = {k: getattr(settings, k) for k in keys}
    yield settings
    for k, v in saved.items():
        setattr(settings, k, v)


# --- The measured profiles must keep their measured values ---

def test_measured_profiles_carry_their_evidence():
    """Three profiles are backed by real measurements; the rest say they aren't.
    Confusing an assertion for evidence is how invented thresholds ship."""
    for name in ("animated", "lecture", "screencast"):
        assert P.PROFILES[name].why.startswith("measured:")
    for name in ("slides", "talking_head"):
        assert "not measured" in P.PROFILES[name].why


def test_animated_uses_the_threshold_that_was_measured():
    """0.3 found 2 frames in a 19-minute animated explainer; 0.15 found 24."""
    assert P.PROFILES["animated"].scene_threshold == 0.15


def test_screencast_dedupes_harder_than_others():
    """Cursor movement and typing over-fire scene detection on a UI."""
    assert P.PROFILES["screencast"].dedupe_threshold > P.PROFILES["animated"].dedupe_threshold


def test_screencast_escalates_more_reluctantly_than_animated():
    """Measured: 82 median OCR words vs ~3 — the UI text IS the content."""
    assert (P.PROFILES["screencast"].escalate_below_words
            < P.PROFILES["animated"].escalate_below_words)


def test_talking_head_spends_nothing():
    assert P.PROFILES["talking_head"].extract_frames is False
    assert P.PROFILES["talking_head"].vlm_max_frames == 0


# --- Selection precedence ---

def test_explicit_profile_beats_source_map(clean_settings):
    settings.profile_source_map = "postman=screencast"
    got = P.resolve(_Src(uploader="Postman"), explicit="animated")
    assert got.name == "animated"


def test_source_map_matches_on_channel(clean_settings):
    settings.profile_source_map = "3blue1brown=animated"
    assert P.resolve(_Src(channel="3Blue1Brown")).name == "animated"


def test_source_map_returns_none_when_unknown(clean_settings):
    settings.profile_source_map = "postman=screencast"
    assert P.resolve(_Src(channel="Some Random Channel")) is None


def test_unknown_explicit_profile_is_an_error():
    with pytest.raises(ValueError, match="Unknown profile"):
        P.resolve(_Src(), explicit="nonsense")


def test_source_map_is_extensible_without_code(clean_settings):
    """Udemy/DataCamp/Kaggle get added here as they are characterised."""
    settings.profile_source_map = "datacamp=screencast"
    assert P.resolve(_Src(url="https://datacamp.com/x")).name == "screencast"


def test_malformed_source_map_entries_are_ignored():
    assert P.parse_source_map("garbage,x=nosuchprofile,postman=screencast") == [
        ("postman", "screencast")
    ]


# --- The probe: classify from free OCR ---

def test_probe_calls_dense_text_a_screencast():
    """Measured Postman median was 82 words of real UI text."""
    dense = ["word " * 80] * 4
    assert P.classify_by_ocr(dense) == "screencast"


def test_probe_calls_sparse_fragments_animated():
    """Measured 3Blue1Brown OCR: '784', 'OOO', 'TITT'."""
    assert P.classify_by_ocr(["784", "OOO", "TITT", "784"]) == "animated"


def test_probe_calls_middling_text_a_lecture():
    assert P.classify_by_ocr(["word " * 35] * 4) == "lecture"


def test_probe_calls_wholly_unreadable_frames_a_talking_head():
    """Nothing readable anywhere: prefer the cheap reading over guessing
    'animated', which would escalate every frame on a hunch."""
    assert P.classify_by_ocr(["", "", "", ""]) == "talking_head"


def test_probe_declines_on_too_few_samples(clean_settings):
    """An unconfident guess silently changes what gets paid for."""
    assert P.classify_by_ocr(["word " * 80]) is None


# --- Applying a profile ---

def test_apply_sets_extraction_and_spend(clean_settings):
    P.apply(P.PROFILES["screencast"])
    assert settings.frame_scene_threshold == 0.15
    assert settings.vlm_max_frames == 10


def test_apply_paid_only_leaves_extraction_alone(clean_settings):
    """Probe results must not move extraction thresholds — the frames are
    already extracted, so acting on them would mean re-extracting for a guess."""
    settings.frame_scene_threshold = 0.42
    P.apply_paid_only(P.PROFILES["screencast"])
    assert settings.frame_scene_threshold == 0.42       # untouched
    assert settings.vlm_escalate_below_words == 8       # applied


def test_probe_never_overrides_the_operator_budget(clean_settings):
    """VLM_MAX_FRAMES is a spending cap the operator set, not a property of the
    content. An inferred profile may decide what *qualifies* for the vision
    model; it may not decide how much you are willing to spend."""
    settings.vlm_max_frames = 2
    P.apply_paid_only(P.PROFILES["talking_head"])
    assert settings.vlm_max_frames == 2                 # budget untouched
    assert settings.vlm_escalate_below_words == 0       # nothing qualifies
