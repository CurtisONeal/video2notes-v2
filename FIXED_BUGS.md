# Fixed bugs

**Why this file exists.** ADRs record *decisions* — why the pipeline is shaped the way it
is. Most bugs fixed here were not decisions; they were defects with a specific cause and a
specific test. Burying them in ADR prose makes them unfindable ("did we already fix the
403 thing?") and makes the ADRs worse at their actual job.

**The recurring pattern is the point:** almost every entry below was found by *running the
thing against real content*, not by reading code. Several contradicted a confident guess.
When a fix here has no test, that is called out — those are the ones likely to regress.

Newest first. Format: symptom → cause → fix → how we know.

---

### yt-dlp staleness causes universal HTTP 403 (twice in four days)
- **Symptom:** every download fails with `HTTP Error 403: Forbidden`. Looks like a site
  problem or an IP block.
- **Cause:** YouTube changed; the pinned yt-dlp is stale. Happened at 8 months stale
  (2026-08-16) and again at 6 weeks stale (2026-08-20).
- **Fix:** bump yt-dlp **in `uv.lock`**, not just the venv — the lockfile pin is what
  caused the staleness, and a venv-only update is undone by the next `uv sync`.
- **Diagnostic that works:** retry a video that downloaded successfully before. If it now
  fails too, the cause is upstream — stop investigating the content.
- **Test:** none possible (external dependency). See ADR-041.

### Intermittent "No such file or directory" during frame extraction
- **Symptom:** 1 video of 7 fails; succeeds on retry. Classic "flaky" write-off.
- **Cause:** `download_video` globbed `source_video.*` and took the first sorted match.
  yt-dlp leaves per-stream fragments (`source_video.f399.mp4`) beside the merged output and
  deletes them after merging — and `f` sorts before `m`, so it picked the doomed fragment.
- **Fix:** skip fragment-named files, pick the largest survivor.
- **Test:** `test_download_prefers_merged_output_over_fragments`.

### Vision model emitted `# Frame Description` inside a `###` block
- **Symptom:** notes' heading hierarchy silently corrupted.
- **Cause:** the model had no way to know its text was being inserted into an existing
  document.
- **Fix:** prompt forbids headings *and explains why*; any heading that survives is
  stripped — a prompt instruction is not a guarantee.
- **Test:** verified across 29 frame blocks, 0 headings.

### Frames could not be correlated with narration
- **Symptom:** a frame at `[3m40s]` had nothing to line up against.
- **Cause:** the summary appends the transcript as raw `full_text` with **no timestamps**.
- **Fix:** each frame block quotes the narration spoken at that moment.
- **Test:** 26 narration blocks across the Postman playlist.

### Fabricated dwell time flattened frame ranking
- **Symptom:** one frame scored 1.00, everything else near 0.
- **Cause:** final-frame dwell computed as `video_duration - timestamp`, but when
  `FRAME_MAX` truncates extraction the last keyframe is just where we stopped looking. A
  1120s video that stopped at 349s credited its last frame with 771 fabricated seconds.
- **Fix:** clamp to the longest gap actually *observed* — not a multiple of the median,
  because transition-heavy content has a ~1s median that would crush a held closing slide.
- **Test:** `test_final_frame_dwell_is_clamped`. (The first fix was wrong; a test caught it.)

### Scene detection under-samples continuously-animated video
- **Symptom:** 1 keyframe from a 25-second video whose screen carried the whole message.
- **Cause:** scene detection assumes cuts; animation has none.
- **Fix:** fall back to interval sampling when frame *count* is too low, so the failure
  self-corrects instead of going silent.
- **Test:** measured 1 → 9 frames; that video went from a 94-byte placeholder to 3797 bytes.

### Budget spent on the first N frames rather than the best N
- **Symptom:** a budget of 8 spent 6 frames inside one 10-second window of near-duplicates.
- **Cause:** escalation walked chronological order and stopped at the cap.
- **Fix:** rank by dwell + uniqueness + audio-cue proximity; spend on the top N.
- **Test:** `tests/test_ranking.py`; changed 6 of 8 selections on real frames.

### `player_client: ['android']` override caused 403s
- **Symptom:** downloads fail; half a course run lost.
- **Cause:** added long ago "for playlist reliability"; YouTube now requires a PO token for
  that client. Measured: android exposed **1** usable audio format vs **5** on defaults.
- **Fix:** removed. Playlists re-verified without it (10/10).
- **Test:** none directly; playlist behaviour covered by integration runs.

### Placeholder API keys reached the provider
- **Symptom:** confusing auth error instead of "no key configured".
- **Cause:** `.env.example` ships `ANTHROPIC_API_KEY=your_key_here`, which is **truthy**, so
  `if not key` passed it through.
- **Fix:** `real_key()` rejects known placeholders.
- **Test:** `test_placeholder_keys_resolve_to_none`.

### `litellm.anthropic_api_key` was a dead attribute
- **Symptom:** Anthropic auth "worked" locally, would fail on any clean machine.
- **Cause:** the real attribute is `anthropic_key`. The assignment created a stray module
  attribute holding the real secret; auth only worked because the key was in the shell env.
- **Fix:** per-call `api_key=`, resolved per provider prefix.
- **Test:** `test_chain_falls_back_to_next_entry` asserts per-provider keys.

### Unit tests silently made live subscription calls
- **Symptom:** suite time jumped 104s → 353s.
- **Cause:** tests patch `litellm.completion`, but the new default chain leads with a
  **subprocess** litellm never sees.
- **Fix:** `pinned_chain` fixture; every hermetic test must pin the chain.
- **Test:** suite runs in ~1s.

### One `None` playlist entry killed an entire run
- **Symptom:** `AttributeError: 'NoneType' object has no attribute 'get'`.
- **Cause:** yt-dlp yields `None` for private/deleted/geo-blocked items.
- **Fix:** skip with a warning naming the position.
- **Test:** `test_probe_source_skips_unavailable_playlist_entries`.

### Caption fetch accepted any URL scheme
- **Symptom:** none observed — found by review.
- **Cause:** caption URLs come from third-party metadata and `urllib` opens `file://`.
  Verified reading `/etc/hosts`.
- **Fix:** http/https only, 8 MB cap, shared by caption fetch and embed scraping.
- **Test:** `test_fetch_refuses_non_http_schemes`.

### CJK caption tracks were rejected as "no usable speech"
- **Symptom:** every Japanese/Chinese/Korean track skipped, with a misleading log line.
- **Cause:** the speech guard counted Latin words only; language selection never looked at
  them either. **Broken for one of the project's two stated domains** (Aikido).
- **Fix:** count CJK by character; `CAPTIONS_LANG` ordered preference with an `any` token.
- **Test:** verified live — 220 cues on a real Japanese track.

### Titles containing `/` truncated recorded provenance
- **Symptom:** `source:  Yamada Sensei.en.json3` — the title silently lost.
- **Cause:** `Path(f"{title}...").name` keeps only the trailing component. A real archived
  title (`Intro to "Aikido..." / Yamada Sensei`) triggered it.
- **Fix:** sanitize before use as a path.
- **Test:** `test_title_with_slash_does_not_truncate_recorded_source`.

### `original_url.txt` recorded an expiring CDN link
- **Symptom:** archived runs could not be re-fetched.
- **Cause:** `entry['url']` on YouTube is a signed, expiring link.
- **Fix:** prefer `webpage_url`.
- **Test:** `test_probe_source_records_canonical_watch_url`.
