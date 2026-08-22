import typer
import re
import shutil
import sys
import time
import datetime as dt
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from video2mdnotes.config import settings
from video2mdnotes.logger import logger
from video2mdnotes.core.downloader import DownloadResult, fetch_audio, probe_source
from video2mdnotes.core.transcriber import transcribe_audio, build_initial_prompt
from video2mdnotes.core.summarizer import generate_summary, SubscriptionExhausted
from video2mdnotes.core.captions import transcript_from_captions
from video2mdnotes.core import frames as frames_mod
from video2mdnotes.core import visuals
from video2mdnotes.core import profiles as profiles_mod

app = typer.Typer(help="Video to Markdown Notes Pipeline")
console = Console()

def _resolve_exhaustion_policy() -> str:
    """Current exhaustion policy, resolving "ask" once by prompting.

    The answer is written back to settings so the rest of the run follows it
    without prompting per video. If there is no TTY (a scheduled or agent-driven
    run), "ask" degrades to "wait" — never to spending money, because nobody is
    there to consent.
    """
    policy = (settings.on_exhaustion or "wait").strip().lower()
    if policy != "ask":
        return policy

    if not sys.stdin.isatty():
        logger.warning("--on-exhaustion=ask with no TTY; waiting for reset instead.")
        settings.on_exhaustion = "wait"
        return "wait"

    console.print("[bold yellow]Subscription capacity exhausted.[/bold yellow]")
    choice = typer.prompt(
        "Continue on [m]etered (costs money), [l]ocal, [w]ait for reset, or [s]top?",
        default="w",
    ).strip().lower()[:1]
    settings.on_exhaustion = {
        "m": "metered", "l": "local", "s": "stop"
    }.get(choice, "wait")
    return settings.on_exhaustion


NO_SUMMARY_PREFIX = "no_summary_"


def _mark_empty(project_dir: Path) -> Path:
    """Rename a project directory to flag that it produced no usable notes."""
    if project_dir.name.startswith(NO_SUMMARY_PREFIX):
        return project_dir
    marked = project_dir.with_name(f"{NO_SUMMARY_PREFIX}{project_dir.name}")
    if marked.exists():
        shutil.rmtree(marked, ignore_errors=True)
    project_dir.rename(marked)
    return marked


def _transcript_segments(project_dir: Path):
    """Recover segment timings from an archived transcript.

    The visuals-only pass has no TranscriptResult in memory, but the archived
    transcript markdown carries `- [H:MM:SS.mmm] text` lines — enough to restore
    the timings the ranker and the narration quotes need.
    """
    from video2mdnotes.core.transcriber import Segment

    files = list((project_dir / "transcripts").glob("*.md"))
    if not files:
        return []
    pattern = re.compile(r"^- \[(\d+):(\d{2}):(\d{2})\.(\d+)\]\s*(.*)$")
    segments = []
    for line in files[0].read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if not m:
            continue
        h, mi, sec, ms, text = m.groups()
        start = int(h) * 3600 + int(mi) * 60 + int(sec) + int(ms) / 1000
        segments.append(Segment(start=start, end=start + 5.0, text=text))
    return segments


def _add_visuals(project_dir: Path, source, summary_path: Path) -> None:
    """Add a visual section to notes that already exist, without re-transcribing.

    Reads the transcript back off disk to recover the segment timings the
    ranker uses for audio cues, so a separate pass ranks frames the same way
    the inline path would.
    """
    from video2mdnotes.core import frames as frames_mod

    video_file = frames_mod.download_video(source.url, project_dir / "_video")
    if not video_file:
        raise RuntimeError("could not download video for frame extraction")
    try:
        keyframes = frames_mod.extract_and_dedupe(video_file, project_dir / "frames")
        if not keyframes:
            logger.info(f"No keyframes extracted for {source.title}")
            return
        segments = _transcript_segments(project_dir)
        readings = visuals.read_frames(keyframes, segments=segments)
        visual_markdown = visuals.render_markdown(readings, segments=segments)
        if not visual_markdown:
            logger.info(f"Frames carried no readable content for {source.title}")
            return

        summary_path.write_text(
            visuals.insert_visual_section(
                summary_path.read_text(encoding="utf-8"), visual_markdown
            ),
            encoding="utf-8",
        )
        logger.success(f"Added {len(readings)} visual(s) to {summary_path.name}")

        # The notes may now be usable even though the audio produced nothing.
        marked = project_dir.name.startswith(NO_SUMMARY_PREFIX)
        if marked and visuals.has_usable_notes(summary_path.read_text(encoding="utf-8")):
            unmarked = project_dir.with_name(project_dir.name[len(NO_SUMMARY_PREFIX):])
            project_dir.rename(unmarked)
            logger.success(f"Visuals rescued empty notes — renamed to {unmarked.name}")
    finally:
        video_file.unlink(missing_ok=True)
        shutil.rmtree(project_dir / "_video", ignore_errors=True)


def _project_root(source) -> Path:
    """Output root for one source, grouped by playlist when asked.

    Grouping is opt-in because turning it on moves where notes land, and a
    library that silently reorganises itself between runs is worse than one
    that scatters predictably.
    """
    from video2mdnotes.core.downloader import sanitize_filename

    root = settings.output_dir
    if settings.group_by_playlist and getattr(source, "playlist_title", None):
        root = root / sanitize_filename(source.playlist_title)
    return root


def _existing_summary(safe_title: str, root: Path | None = None) -> Path | None:
    """Find an already-generated summary for this video, if any.

    Matched on title independent of run date, because the project directory is
    named `<date>_<title>` and a resume the next day must still recognise work
    finished today.
    """
    root = root or settings.output_dir
    # Search the grouped directory and the output root, so notes made before
    # --group-by-playlist existed are still found and not silently redone.
    for base in {root, settings.output_dir}:
        if not base.exists():
            continue
        for candidate in base.glob(f"*_{safe_title}"):
            summary = candidate / "summaries" / f"{safe_title}.summary.md"
            if summary.exists() and summary.stat().st_size > 0:
                return summary
    return None


def _wait_for_reset(exhausted: SubscriptionExhausted) -> None:
    """Sleep until the subscription limit resets, then let the caller retry."""
    now = dt.datetime.now()
    if exhausted.reset_at and exhausted.reset_at > now:
        seconds = (exhausted.reset_at - now).total_seconds()
        source = f"reset time reported by the CLI ({exhausted.reset_at:%Y-%m-%d %H:%M})"
    else:
        seconds = settings.exhaustion_wait_seconds
        source = "no reset time reported — using EXHAUSTION_WAIT_SECONDS"

    seconds = min(seconds, settings.exhaustion_max_wait_seconds)
    resume_at = now + dt.timedelta(seconds=seconds)

    console.print(Panel(
        f"[bold yellow]Subscription capacity exhausted.[/bold yellow]\n\n"
        f"Not falling back to a paid backend — waiting for capacity you already\n"
        f"pay for. Override with [bold]--on-exhaustion metered[/bold] (or "
        f"[bold]local[/bold]/[bold]stop[/bold]).\n\n"
        f"{source}\n"
        f"Waiting {seconds/3600:.1f}h, resuming about {resume_at:%H:%M}.\n\n"
        f"Safe to Ctrl-C: finished videos are on disk and will be skipped when\n"
        f"you re-run the same command.",
        title="Waiting for limit reset",
        border_style="yellow",
    ))
    logger.warning(f"Subscription exhausted; sleeping {seconds:.0f}s until ~{resume_at:%H:%M}.")
    time.sleep(seconds)


@app.command()
def process(
    url: str = typer.Argument(..., help="The URL of the video or playlist to process"),
    keep_wav: bool = typer.Option(True, help="Keep the downloaded WAV file in the archive"),
    force: bool = typer.Option(
        False, "--force",
        help="Re-summarize videos that already have a summary (default: skip them)",
    ),
    group_by_playlist: bool = typer.Option(
        False, "--group-by-playlist",
        help="Put all of a playlist's notes in one directory named after the playlist.",
    ),
    visuals_only: bool = typer.Option(
        False, "--visuals-only",
        help="Add visual content to notes that already exist, without re-transcribing.",
    ),
    profile: str = typer.Option(
        None, "--profile",
        help="Content shape: animated | lecture | screencast | slides | talking_head. "
             "Overrides the source map and the probe.",
    ),
    on_exhaustion: str = typer.Option(
        None, "--on-exhaustion",
        help="When the subscription runs out: wait | metered | local | stop | ask. "
             "Default 'wait' — never starts spending money unattended.",
    ),
):
    """
    Downloads, transcribes, and summarizes a video or playlist from a URL.
    """
    if on_exhaustion:
        settings.on_exhaustion = on_exhaustion.strip().lower()
    if group_by_playlist:
        settings.group_by_playlist = True
    if visuals_only:
        # The whole point of this mode is to add visuals, so enabling it
        # implicitly beats failing with "nothing to do".
        settings.extract_frames = True

    logger.info(f"Starting processing for URL: {url}")

    from video2mdnotes.core.downloader import sanitize_filename

    # 1. Probe (metadata + caption availability; no audio yet)
    try:
        logger.info("Step 1: Probing source...")
        sources = probe_source(url)
        logger.success(f"Found {len(sources)} videos.")
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise typer.Exit(code=1)

    # A profile mutates settings for one video; snapshot the configured globals
    # so a screencast profile cannot silently leak into the next video's run.
    _profile_defaults = {
        k: getattr(settings, k) for k in (
            "frame_scene_threshold", "frame_dedupe_threshold", "frame_max",
            "vlm_escalate_below_words", "vlm_max_frames", "vlm_model",
            "extract_frames",
        )
    }

    done: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []
    stopped_at: str | None = None

    for index, source in enumerate(sources, 1):
        position = f"{index}/{len(sources)}"

        # Resume: work already on disk is not redone. Re-running a playlist
        # after an interruption must not re-summarize what it already has —
        # that is the expensive half of the run.
        for _k, _v in _profile_defaults.items():
            setattr(settings, _k, _v)
        try:
            chosen = profiles_mod.resolve(source, profile)
        except ValueError as e:
            logger.error(str(e))
            raise typer.Exit(code=2)
        settings.__dict__['_profile_locked'] = bool(chosen)
        if chosen:
            profiles_mod.apply(chosen)

        project_root = _project_root(source)

        # --visuals-only adds to notes that already exist; it never transcribes.
        if visuals_only:
            existing = _existing_summary(sanitize_filename(source.title), project_root)
            if not existing:
                logger.warning(f"[{position}] No existing notes to add visuals to: {source.title}")
                failed.append((source.title, "no existing notes"))
                continue
            try:
                _add_visuals(existing.parent.parent, source, existing)
                done.append(source.title)
            except Exception as e:  # noqa: BLE001
                logger.error(f"[{position}] Visuals failed: {source.title} — {e}")
                failed.append((source.title, str(e)))
            continue

        already = _existing_summary(sanitize_filename(source.title), project_root)
        if already and not force:
            logger.info(f"[{position}] Skipping (already summarized): {source.title}")
            skipped.append(source.title)
            continue

        # Per-video isolation: one bad video must not abandon the rest of a
        # playlist. Only exhaustion (handled below) stops the whole run.
        try:
            logger.info(f"[{position}] Processing: {source.title}")

            # 2. Transcript — captions first, Whisper as the fallback.
            logger.info("Step 2: Obtaining Transcript...")
            transcript_result = None
            if settings.captions_first:
                transcript_result = transcript_from_captions(
                    title=source.title, subtitles=source.subtitles
                )
                if transcript_result is None and source.has_automatic_captions:
                    logger.info(
                        "Only machine captions available — using Whisper instead "
                        "(auto-captions are ASR without our vocabulary hint)."
                    )

            audio_path = None
            if transcript_result is None:
                audio_path = fetch_audio(source)
                initial_prompt = build_initial_prompt(
                    title=source.title,
                    tags=source.tags,
                    description=source.description
                )
                transcript_result = transcribe_audio(
                    audio_path,
                    title=source.title,
                    initial_prompt=initial_prompt
                )

            download_result = DownloadResult(
                audio_path=audio_path,
                title=source.title,
                url=source.url,
                download_date=dt.date.today(),
                tags=source.tags,
                description=source.description,
            )
            logger.success(
                f"Transcript ready via {transcript_result.transcript_source}: "
                f"{len(transcript_result.segments)} segments"
            )

            # 2b. Archive the transcript NOW, before anything can fail.
            # Whisper is the expensive step; a summarizer failure (exhaustion,
            # provider error) used to discard it entirely and force a full
            # re-transcription on retry. Writing here also makes the transcript
            # a durable artifact that can be re-summarized with a different
            # prompt without touching the audio again.
            safe_title = sanitize_filename(source.title)
            date_str = dt.date.today().strftime('%Y%m%d')
            project_dir = project_root / f"{date_str}_{safe_title}"
            (project_dir / "transcripts").mkdir(parents=True, exist_ok=True)
            transcript_path = project_dir / "transcripts" / f"{safe_title}.md"
            transcript_path.write_text(
                transcript_result.markdown_content, encoding="utf-8"
            )
            (project_dir / "original_url.txt").write_text(source.url, encoding="utf-8")

            # 3. Summarize — retries across a limit reset when policy is "wait".
            logger.info("Step 3: Generating Summary...")
            while True:
                try:
                    summary_result = generate_summary(transcript_result)
                    break
                except SubscriptionExhausted as e:
                    if _resolve_exhaustion_policy() != "wait":
                        raise
                    _wait_for_reset(e)
            logger.success("Summary Generated.")

            # 4. Archive / Output
            logger.info("Step 4: Archiving Results...")
            
            from video2mdnotes.core.downloader import sanitize_filename
            safe_title = sanitize_filename(download_result.title)
            date_str = dt.date.today().strftime('%Y%m%d')
            project_dir_name = f"{date_str}_{safe_title}"
            
            project_dir = project_root / project_dir_name
            project_dir.mkdir(parents=True, exist_ok=True)

            transcripts_dir = project_dir / "transcripts"
            summaries_dir = project_dir / "summaries"

            transcripts_dir.mkdir(exist_ok=True)
            summaries_dir.mkdir(exist_ok=True)

            # No audio exists on the captions path — nothing to archive or clean up.
            dest_wav = None
            if download_result.audio_path is not None:
                wav_dir = project_dir / "wav_files"
                wav_dir.mkdir(exist_ok=True)
                if keep_wav:
                    dest_wav = wav_dir / download_result.audio_path.name
                    shutil.move(str(download_result.audio_path), str(dest_wav))
                else:
                    download_result.audio_path.unlink()

            # 3b. Visual content — opt-in; the vision tier is metered spend.
            visual_markdown = ""
            if settings.extract_frames:
                logger.info("Extracting visual content from keyframes...")
                try:
                    video_file = frames_mod.download_video(source.url, project_dir / "_video")
                    if video_file:
                        keyframes = frames_mod.extract_and_dedupe(
                            video_file, project_dir / "frames"
                        )
                        # Transcript segments feed the audio-cue ranking
                        # signal ("as you can see here"); duration bounds the
                        # final frame's dwell.
                        readings = visuals.read_frames(
                            keyframes,
                            segments=transcript_result.segments,
                            video_duration=(
                                transcript_result.segments[-1].end
                                if transcript_result.segments else None
                            ),
                        )
                        visual_markdown = visuals.render_markdown(
                            readings, segments=transcript_result.segments
                        )
                        video_file.unlink(missing_ok=True)
                        shutil.rmtree(project_dir / "_video", ignore_errors=True)
                except Exception as e:  # noqa: BLE001 - enrichment is never fatal
                    logger.warning(f"Visual extraction failed: {e}")

            summary_path = summaries_dir / f"{safe_title}.summary.md"
            summary_text = visuals.insert_visual_section(
                summary_result.summary_text, visual_markdown
            )
            summary_path.write_text(summary_text, encoding="utf-8")

            # A run that produced no usable notes (silent/music-only source with
            # nothing on screen either) is a legitimate outcome, but in a
            # listing it looks identical to a real result. Mark it.
            if settings.mark_empty_results and not visuals.has_usable_notes(summary_text):
                project_dir = _mark_empty(project_dir)
                summary_path = project_dir / "summaries" / summary_path.name
                logger.warning(
                    f"[{position}] No usable notes produced — marked "
                    f"{project_dir.name}"
                )

            console.print(Panel(
                f"[bold]Processing Complete for {download_result.title}![/bold]\n\n"
                f"Output Directory: [blue]{project_dir}[/blue]\n"
                f"Summary: [blue]{summary_path}[/blue]",
                title="Success",
                border_style="green"
            ))
            done.append(source.title)

        except SubscriptionExhausted as e:
            # Policy is not "wait" (that retries in place), so end the run here
            # rather than burn the rest of the playlist on failures or spend.
            logger.error(f"[{position}] Subscription exhausted: {e}")
            stopped_at = f"{position} — {source.title}"
            break
        except KeyboardInterrupt:
            stopped_at = f"{position} — {source.title} (interrupted)"
            break
        except Exception as e:  # noqa: BLE001 - one bad video must not end the run
            logger.error(f"[{position}] Failed: {source.title} — {e}")
            failed.append((source.title, str(e)))
            continue

    # Final ledger, so an unattended run leaves a readable account of itself.
    lines = [
        f"[green]Summarized:[/green] {len(done)}",
        f"[blue]Skipped (already done):[/blue] {len(skipped)}",
        f"[red]Failed:[/red] {len(failed)}",
    ]
    for title, err in failed:
        lines.append(f"  [red]•[/red] {title[:50]} — {err[:60]}")
    if stopped_at:
        remaining = len(sources) - len(done) - len(skipped) - len(failed)
        lines.append(f"\n[yellow]Stopped at {stopped_at}[/yellow]")
        lines.append(f"[yellow]{remaining} video(s) not attempted.[/yellow]")
        lines.append("Re-run the same command to resume — finished videos are skipped.")

    console.print(Panel(
        "\n".join(lines),
        title="Run Summary" if not stopped_at else "Run Stopped",
        border_style="green" if not (failed or stopped_at) else "yellow",
    ))

    if stopped_at or failed:
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
