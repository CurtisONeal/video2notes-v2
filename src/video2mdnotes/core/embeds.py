"""Recover playable video URLs from a page yt-dlp cannot handle directly.

Course platforms, docs sites and blogs frequently wrap third-party video in
their own chrome. yt-dlp's generic extractor only sees markup present in the
served HTML, so when the player is injected by JavaScript it reports
"Unsupported URL" and the page is unusable — even though the underlying videos
are ordinary public YouTube/Vimeo items the pipeline handles perfectly.

Observed case: Anthropic's Skilljar course pages. `probe_source()` failed with
"Unsupported URL", while a plain fetch of the same page contained eight
`youtube.com/embed/<id>` references.

This scrapes those references so the normal path can take over. It deliberately
does not attempt to log in, execute JavaScript, or defeat any access control: a
page that does not serve embed URLs to an anonymous fetch simply yields nothing.
"""

import re
from typing import List

from video2mdnotes.logger import logger
from video2mdnotes.core.webfetch import fetch_text

# Ordered so the canonical watch URL is what we hand back to yt-dlp.
_PATTERNS = (
    # youtube.com/embed/<id>, youtube-nocookie.com/embed/<id>
    (re.compile(r"youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]{11})"),
     "https://www.youtube.com/watch?v={0}"),
    # youtu.be/<id>
    (re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
     "https://www.youtube.com/watch?v={0}"),
    # youtube.com/watch?v=<id>
    (re.compile(r"youtube\.com/watch\?v=([A-Za-z0-9_-]{11})"),
     "https://www.youtube.com/watch?v={0}"),
    # player.vimeo.com/video/<id> and vimeo.com/<id>
    (re.compile(r"player\.vimeo\.com/video/(\d{6,})"), "https://vimeo.com/{0}"),
    (re.compile(r"vimeo\.com/(\d{6,})"), "https://vimeo.com/{0}"),
)

# A page with hundreds of embeds is far more likely to be a listing page than
# something anyone meant to transcribe. Cap it rather than fan out unbounded.
MAX_EMBEDS = 25


def extract_embed_urls(html: str, max_embeds: int = MAX_EMBEDS) -> List[str]:
    """Find embedded video URLs in page HTML, de-duplicated, in document order."""
    found: List[str] = []
    seen = set()

    # Sort matches by position so the returned order follows the page, which is
    # usually lesson order on a course page.
    hits = []
    for pattern, template in _PATTERNS:
        for match in pattern.finditer(html or ""):
            hits.append((match.start(), template.format(match.group(1))))

    for _, url in sorted(hits, key=lambda pair: pair[0]):
        if url not in seen:
            seen.add(url)
            found.append(url)
        if len(found) >= max_embeds:
            break
    return found


def scrape_embed_urls(page_url: str, max_embeds: int = MAX_EMBEDS) -> List[str]:
    """Fetch a page and return the embedded video URLs it exposes.

    Returns an empty list on any failure — the caller should then surface the
    original yt-dlp error, since "we could not scrape it either" is not a more
    useful message than "unsupported URL".
    """
    try:
        html = fetch_text(page_url)
    except Exception as e:  # noqa: BLE001 - scraping is best-effort by design
        logger.warning(f"Could not fetch {page_url} to look for embeds: {e}")
        return []

    urls = extract_embed_urls(html, max_embeds=max_embeds)
    if urls:
        logger.success(f"Found {len(urls)} embedded video(s) on {page_url}")
    return urls
