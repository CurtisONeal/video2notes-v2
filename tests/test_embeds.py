import pytest
from unittest.mock import MagicMock, patch

from video2mdnotes.core.embeds import extract_embed_urls, scrape_embed_urls
from video2mdnotes.core.webfetch import fetch_text


# --- Extraction ---

def test_extracts_youtube_iframe_embed():
    """The observed real case: a course page whose player is a YouTube iframe."""
    html = '<iframe src="https://www.youtube.com/embed/l9sZFo3TfRo?rel=0"></iframe>'
    assert extract_embed_urls(html) == ["https://www.youtube.com/watch?v=l9sZFo3TfRo"]


def test_extracts_nocookie_and_short_and_watch_forms():
    html = """
      <iframe src="https://www.youtube-nocookie.com/embed/aaaaaaaaaaa"></iframe>
      <a href="https://youtu.be/bbbbbbbbbbb">short</a>
      <a href="https://www.youtube.com/watch?v=ccccccccccc">watch</a>
    """
    assert extract_embed_urls(html) == [
        "https://www.youtube.com/watch?v=aaaaaaaaaaa",
        "https://www.youtube.com/watch?v=bbbbbbbbbbb",
        "https://www.youtube.com/watch?v=ccccccccccc",
    ]


def test_deduplicates_same_video_referenced_twice():
    """Pages routinely reference one video as both an iframe and a share link."""
    html = ('<iframe src="https://www.youtube.com/embed/l9sZFo3TfRo"></iframe>'
            '<a href="https://youtu.be/l9sZFo3TfRo">Watch on YouTube</a>')
    assert extract_embed_urls(html) == ["https://www.youtube.com/watch?v=l9sZFo3TfRo"]


def test_extracts_vimeo():
    html = '<iframe src="https://player.vimeo.com/video/123456789"></iframe>'
    assert extract_embed_urls(html) == ["https://vimeo.com/123456789"]


def test_ignores_channel_and_non_video_links():
    """A channel link is not a video and must not become a bogus source."""
    html = '<a href="https://www.youtube.com/@anthropic-ai">channel</a>'
    assert extract_embed_urls(html) == []


def test_returns_document_order():
    """Course pages list lessons in order; preserve it."""
    html = ('<iframe src="https://www.youtube.com/embed/zzzzzzzzzzz"></iframe>'
            '<iframe src="https://www.youtube.com/embed/aaaaaaaaaaa"></iframe>')
    assert extract_embed_urls(html) == [
        "https://www.youtube.com/watch?v=zzzzzzzzzzz",
        "https://www.youtube.com/watch?v=aaaaaaaaaaa",
    ]


def test_caps_number_of_embeds():
    """A listing page with hundreds of embeds must not fan out unbounded."""
    html = "".join(
        f'<iframe src="https://www.youtube.com/embed/{i:011d}"></iframe>' for i in range(60)
    )
    assert len(extract_embed_urls(html, max_embeds=25)) == 25


def test_empty_html_is_safe():
    assert extract_embed_urls("") == []
    assert extract_embed_urls(None) == []


# --- Fetch hardening (shared with the captions path) ---

@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://h/x", "data:text/html,x"])
def test_fetch_text_refuses_non_http_schemes(url):
    """Embed scraping widens the set of URLs reaching the fetcher."""
    with pytest.raises(ValueError, match="scheme"):
        fetch_text(url)


def test_fetch_text_rejects_oversized_body():
    class _Resp:
        def read(self, n): return b"x" * n
        def __enter__(self): return self
        def __exit__(self, *a): return False

    with patch("video2mdnotes.core.webfetch.urllib.request.urlopen", return_value=_Resp()):
        with pytest.raises(ValueError, match="exceeds"):
            fetch_text("https://example.test/big", max_bytes=1024)


def test_scrape_returns_empty_on_fetch_failure():
    """A failure here must fall back to the original yt-dlp error, not raise."""
    with patch("video2mdnotes.core.embeds.fetch_text", side_effect=OSError("boom")):
        assert scrape_embed_urls("https://example.test/course") == []


# --- probe_source integration ---

def test_probe_source_scrapes_when_ytdlp_rejects_url():
    """The Skilljar case: yt-dlp says Unsupported URL, embeds save the run."""
    import yt_dlp
    from video2mdnotes.core.downloader import probe_source

    # First call (the page) is unsupported; the recursive call for the scraped
    # embed succeeds.
    calls = {"n": 0}

    def _extract(url, download=False):
        calls["n"] += 1
        if calls["n"] == 1:
            raise yt_dlp.utils.DownloadError("Unsupported URL: https://example.test/course")
        return {"title": "Embedded", "webpage_url": url}

    ydl = MagicMock()
    ydl.__enter__.return_value.extract_info.side_effect = _extract

    with patch("video2mdnotes.core.downloader.yt_dlp.YoutubeDL", return_value=ydl), \
         patch("video2mdnotes.core.downloader.scrape_embed_urls",
               return_value=["https://www.youtube.com/watch?v=aaaaaaaaaaa"]) as scrape:
        sources = probe_source("https://example.test/course")

    scrape.assert_called_once_with("https://example.test/course")
    assert [s.title for s in sources] == ["Embedded"]
    assert sources[0].url == "https://www.youtube.com/watch?v=aaaaaaaaaaa"


def test_probe_source_does_not_scrape_recursively():
    """An embed must not trigger another round of page scraping."""
    import yt_dlp
    from video2mdnotes.core.downloader import probe_source

    ydl = MagicMock()
    ydl.__enter__.return_value.extract_info.side_effect = yt_dlp.utils.DownloadError("Unsupported URL")

    with patch("video2mdnotes.core.downloader.yt_dlp.YoutubeDL", return_value=ydl), \
         patch("video2mdnotes.core.downloader.scrape_embed_urls") as scrape:
        with pytest.raises(yt_dlp.utils.DownloadError):
            probe_source("https://example.test/x", allow_embed_scrape=False)
        scrape.assert_not_called()
