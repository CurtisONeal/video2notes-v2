"""One hardened HTTP fetch, shared by everything that pulls third-party URLs.

Caption tracks and embed-scraped pages both come from metadata we do not
control, so the same two restrictions apply to both. Keeping them in one place
means they cannot drift apart: a second copy of this logic is exactly the sort
of thing that gets a scheme check on one path and not the other.
"""

import urllib.parse
import urllib.request

# urllib opens file:// (and ftp://, data:) quite happily. A URL taken from page
# metadata must never be able to read a local file into the pipeline, where it
# would land in a transcript and then in an archived summary.
ALLOWED_SCHEMES = ("http", "https")

DEFAULT_MAX_BYTES = 8 * 1024 * 1024
USER_AGENT = "Mozilla/5.0"


def fetch_text(url: str, max_bytes: int = DEFAULT_MAX_BYTES, timeout: int = 30) -> str:
    """Fetch a URL as text over http(s) only, refusing oversized responses.

    Raises:
        ValueError: if the scheme is not http/https, or the body exceeds max_bytes.
    """
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Refusing URL with scheme {scheme!r}")

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        # One byte past the cap, so an oversized body is detected rather than
        # silently truncated into something that still looks parseable.
        raw = response.read(max_bytes + 1)

    if len(raw) > max_bytes:
        raise ValueError(f"Response exceeds {max_bytes} bytes")
    return raw.decode("utf-8", errors="replace")
