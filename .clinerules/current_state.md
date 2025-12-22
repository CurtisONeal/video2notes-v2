Summary of what I read

.clinerules: ClineRules.txt, descriptive_video_transcribing_fast_iteration_loop.md, human_todo_list.md, Proj_requirements.md. Key flow: URL -> yt-dlp (audio-only) -> faster-whisper -> Markdown/JSON -> Obsidian. Cookies and later FastAPI / Chrome-extension phases noted.
Root/actionable files reviewed: transcribe_dir.py, batch_run.sh, clean_dir_filenames.sh (converted from your aliases), .gitignore, summarize_prompt.txt and yt-dlp command notes in .clinerules.
Phase differences (current vs planned)

Initial/manual phase (we are in this now): run yt-dlp to download WAV(s) locally, run filename-cleaning script, run transcribe_dir.py to produce /transcripts/*.md, run batch_run.sh (summaries). Human/optional cleanup or manual edits afterwards.
Second/automated phase (planned later): single Python CLI (transcribe --url ...) or FastAPI endpoint that runs yt-dlp + faster-whisper + markdown output automatically; uses .env for settings and a configurable output dir.
Later phases: Chrome extension + backend service, Obsidian sync, more automation.
Current behavior of actionable scripts (what they actually do now)

yt-dlp (manual command in docs): downloads audio .wav files to project root (or specified folder).
clean_dir_filenames.sh: renames files in a directory to safe names (spaces->, dashes->, prefix ISO date, lowercase, strip special chars). Has safe/dry-run behavior.
transcribe_dir.py:
Scans BASE_DIR (script's repo folder) for .wav files.
Writes transcripts to /transcripts (OUTDIR) - creates folder if missing.
After successfully writing a transcript, moves the .wav into transcribed_wav/.
Skips transcription if transcript already exists (does not overwrite).
batch_run.sh:
Iterates transcripts/*.md and runs summarization (calls your llm or summarizer using summarize_prompt.txt).
Writes outputs to /summaries.
After successful summarization, moves WAVs from transcribed_wav/ into transcribed_wav/archive/ (creates archive dir) - handles missing files gracefully.
.gitignore:
Ignores contents of transcripts, summaries, results, transcribed_wav (keeps .gitkeep placeholders so directories remain tracked).
Notes: formatter/linter settings set project-wide to autopep8/pycodestyle (workspace .vscode/settings.json).
Recommended run order (what should be run and why)

yt-dlp -> download audio (.wav) into project root (or configured input dir).
./clean_dir_filenames.sh [--dry-run] -> sanitize filenames so downstream code sees safe names.
python transcribe_dir.py -> transcribe all .wav in project root; produces transcripts/*.md and moves processed .wav -> transcribed_wav/.
batch_run.sh -> summarize transcripts/*.md -> summaries/ and move archived wavs transcribed_wav/archive/.
Manual QA / human edits in summaries/transcripts (or additional cleanup script).
Quick test to validate the pipeline (run these from project root)

Show WAVs to process:
Dry-run filename cleanup (verify changes first):
Apply cleanup:
Transcribe all found WAVs:
Run summarization:
Checks to ensure Git won't include large/unwanted files

List WAV files currently tracked by git:
If any tracked WAVs should be untracked:
Edge-cases / recommendations (short)

If you want transcripts overwritten, change transcribe_dir.py behavior (currently skips existing .md).
If many large WAVs were already committed, consider git-lfs or removing them from history (I can help).
I can run the test steps here, or update scripts (e.g., always move wavs even if transcript exists) - tell me which.
Do you want me to run the pipeline test now (I'll run the commands and report results), or update any script behaviors?
