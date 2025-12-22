# Current Task: Modern Python Rewrite (uv + hatchling)

## Major Phase Goal
**Implement a modern, fully Python version of the video2mdnotes pipeline using uv for dependency management and hatchling for packaging.**

The goal is to replace the current mix of Bash and Python scripts with a unified, modular Python application. This application must be designed from the ground up to be:
1.  **Docker-ready:** Runs cleanly in a container (initially local).
2.  **FastAPI-ready:** Core logic is decoupled from the CLI so it can be served via an API.
3.  **Testable:** Each component has verifiable success criteria.

---

## Current Requirements & Implementation Plan

### 1. Project Initialization & Infrastructure
*   **Goal:** Set up a professional Python project structure.
*   **Architecture:**
    *   Use pyproject.toml with hatchling build backend.
    *   Use uv for virtual environment and dependency locking.
    *   Implement pydantic-settings for typed configuration (loading .env).
*   **Dependencies:**
    *   **Prod:** faster-whisper, yt-dlp, rich, pydantic-settings, litellm, typer.
    *   **Dev:** pytest, ruff, mypy.
*   **Plan:**
    1.  Create pyproject.toml with all dependencies.
    2.  Create src/video2mdnotes/ package structure.
    3.  Create config.py using Pydantic BaseSettings.
    4.  Create tests/test_config.py to verify loading.
*   **Result:**
    *   [COMPLETE] pyproject.toml created.
    *   [COMPLETE] Dependencies installed via uv sync.
    *   [COMPLETE] config.py implemented.
    *   [COMPLETE] Tests passed (3/3).

### 2. Module: Downloader (yt-dlp wrapper)
*   **Goal:** Replace manual yt-dlp commands and clean_dir_filenames.sh.
*   **Architecture:**
    *   Input: URL string.
    *   Output: Path to downloaded .wav file and metadata (Title, URL, Date).
    *   Logic:
        *   Download audio as WAV.
        *   Sanitize filename (using the logic from clean_dir_filenames.sh).
        *   Save metadata to a JSON or object for passing to the next stage.
*   **Limitations (Phase 1):**
    *   Only supports direct yt-dlp URLs (no complex JS streaming).
*   **Plan:**
    1.  Create src/video2mdnotes/core/downloader.py.
    2.  Implement DownloadResult Pydantic model.
    3.  Implement sanitize_filename (regex: replace space/dash with underscore, lower, strip special).
    4.  Implement download_audio using yt_dlp.YoutubeDL.
    5.  Create tests/test_downloader.py with unit and integration tests.
*   **Result:**
    *   [COMPLETE] downloader.py implemented.
    *   [COMPLETE] Tests passed (7/7).

### 3. Module: Transcriber (faster-whisper wrapper)
*   **Goal:** Port transcribe_dir.py into the modular architecture.
*   **Architecture:**
    *   Input: Path to .wav file.
    *   Output: Path to raw transcript (Markdown/Text) and segments data.
    *   Logic:
        *   Load model (cached).
        *   Transcribe with progress bar (Rich).
        *   Return structured transcript object.
*   **Plan:**
    1.  Refactor transcribe_dir.py into src/video2mdnotes/core/transcriber.py.
    2.  Implement TranscriptResult Pydantic model.
    3.  Implement transcribe_audio function using faster_whisper.
    4.  Create tests/test_transcriber.py with mocked unit tests and integration tests.
*   **Result:**
    *   [COMPLETE] transcriber.py implemented.
    *   [COMPLETE] Tests passed (9/9).

### 4. Module: Summarizer (litellm integration)
*   **Goal:** Replace batch_run.sh with a robust Python module.
*   **Architecture:**
    *   Input: Transcript text/file.
    *   Output: Summary Markdown file.
    *   Logic:
        *   Use litellm for multi-provider LLM calls.
        *   Construct prompt using summarize_prompt.txt.
        *   Call LLM and save result.
*   **Plan:**
    1.  Implement src/video2mdnotes/core/summarizer.py using litellm.
    2.  Implement SummaryResult Pydantic model.
    3.  Implement generate_summary function.
    4.  Create tests/test_summarizer.py with mocked unit tests and integration tests.
*   **Result:**
    *   [COMPLETE] summarizer.py implemented.
    *   [COMPLETE] Tests passed (12/12).
    *   [NOTE] The warning (PydanticSerializationUnexpectedValue) is coming from litellm's internal Pydantic models when serializing the response. It's a known warning in some versions of litellm interacting with Pydantic v2, but it doesn't affect the functionality or the correctness of our code. We can safely ignore it for now.

### 5. Module: Orchestrator & CLI
*   **Goal:** Tie it all together into a single command and define the output logic.
*   **Architecture:**
    *   Command: video2mdnotes process <URL>
    *   Output Modes: Local (default) vs Cloud.
    *   Logic: Downloader -> Transcriber -> Summarizer -> Archive/Return.
*   **Plan:**
    1.  Implement src/video2mdnotes/main.py with typer.
    2.  Implement the "Project-Based Archiving" logic (create folder, move files).
    3.  Create tests/e2e/test_full_pipeline.py for the end-to-end test.
*   **Result:**
    *   (Pending)

### 6. Dockerization (Local)
*   **Goal:** Run the CLI inside a container.
*   **Architecture:**
    *   Dockerfile using multi-stage build (uv for install).
    *   Volumes for: Output data, Model cache, Config.
*   **Plan:**
    1.  Write Dockerfile.
    2.  Write docker-compose.yml.
*   **Result:**
    *   (Pending)

---

## Later Requirements (Future Phase)
*   **FastAPI Implementation:** Expose endpoints for URL and File processing.
*   **Chrome Extension:** Extract audio from streaming sites via Web Audio API.
*   **Cloud Deployment:** Deploy to Cloud Run / AWS ECS.
