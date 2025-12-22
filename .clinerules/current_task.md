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
    *   [COMPLETE] main.py implemented with loguru logging.
    *   [COMPLETE] E2E test passed (13/13).

### 6. Dockerization (Local)
*   **Goal:** Run the CLI inside a container.
*   **Architecture:**
    *   Dockerfile using multi-stage build (uv for install).
    *   Volumes for: Output data, Model cache, Config.
*   **Dependencies:**
    *   Docker Desktop (for Mac/Windows) or Docker Engine (for Linux) must be running.
*   **Plan:**
    1.  Create .dockerignore to exclude unnecessary files from the build context.
    2.  Create Dockerfile using a multi-stage build (Builder -> Runtime).
    3.  Install system dependencies like ffmpeg in the runtime stage.
    4.  Set up the entrypoint to run the Python CLI application.
    5.  Create docker-compose.yml to simplify running the container with correct volume mounts for output, model cache, and the .env file.
*   **Result:**
    *   [COMPLETE] .dockerignore created.
    *   [COMPLETE] Dockerfile created.
    *   [COMPLETE] docker-compose.yml created.
    *   [COMPLETE] Test run successful.

### 7. Enhancement: Add Deno to Docker Image
*   **Goal:** Make yt-dlp more robust by providing a JavaScript runtime.
*   **Architecture:**
    *   Add `unzip` and `curl` to the Docker image's system dependencies.
    *   Download and install `deno` via its official install script.
    *   Add the deno binary to the container's `PATH`.
*   **Plan:**
    1.  Modify the `RUN` command in the `Dockerfile` to include `unzip` and the `deno` installation.
    2.  Update the `ENV PATH` to include `/root/.deno/bin`.
*   **Result:**
    *   [DEFERRED] See "Known Issues & Future Fixes".

### 8. Enhancement: Playlist Support
*   **Goal:** Enable the `process` command to handle playlist URLs, processing each video sequentially.
*   **Architecture:**
    *   `downloader.py`: The `download_audio` function must be updated to detect a playlist URL and return a `List[DownloadResult]` instead of a single object.
    *   `main.py`: The main `process` function must be updated to loop through the list of `DownloadResult` objects, running the transcribe, summarize, and archive steps for each one.
*   **Plan:**
    1.  Refactor `downloader.py` to detect playlist metadata and loop through entries, returning a list of results.
    2.  Update the main loop in `main.py` to iterate over the list of downloads.
    3.  Create a new E2E test using a small, stable playlist URL to verify the functionality.
*   **Result:**
    *   [COMPLETE] downloader.py refactored.
    *   [COMPLETE] main.py refactored.
    *   [COMPLETE] Tests passed (14/14).

### 9. Enhancement: FastAPI Interface
*   **Goal:** Expose the processing pipeline via a REST API with Swagger UI.
*   **Architecture:**
    *   Add `fastapi` and `uvicorn` dependencies.
    *   Create `src/video2mdnotes/api.py` to define the FastAPI app and endpoints.
    *   Implement `POST /process` to accept a URL and run the pipeline in a background task.
    *   Update `docker-compose.yml` to add an `api` service that runs `uvicorn`.
*   **Plan:**
    1.  Update `pyproject.toml` with new dependencies.
    2.  Create `src/video2mdnotes/api.py`.
    3.  Update `docker-compose.yml` to add the `api` service with port mapping `8000:8000`.
*   **Result:**
    *   [COMPLETE] api.py implemented.
    *   [COMPLETE] docker-compose.yml updated.
    *   [COMPLETE] Manual test successful.

---

## Known Issues & Future Fixes

### yt-dlp JavaScript Runtime Warning
*   **Issue:** `yt-dlp` still shows warnings about a missing JavaScript runtime, even after `deno` was added to the Docker image.
*   **Hypothesis:** `yt-dlp` may require an explicit command-line argument (e.g., `--js-runtime deno`) or a configuration file to use the installed runtime. The current implementation does not provide this.
*   **Status:** This is a low-priority issue as downloads are still succeeding. It can be addressed in a future enhancement phase.

---

## Side Quests, Errors & Learnings

### Typer Single-Command Behavior
*   **Issue:** When a `typer` application has only one command (e.g., just `process`), Typer treats that command as the "main" entry point.
*   **Symptom:** Invoking `runner.invoke(app, ["process", url])` fails with exit code 2 (Usage Error) because Typer expects `runner.invoke(app, [url])`.
*   **Resolution:** Adjusted the test invocation to match Typer's single-command behavior.

### Docker Compose V2 Command
*   **Issue:** The `docker-compose` (hyphenated) command is deprecated in modern Docker versions.
*   **Symptom:** `zsh: command not found: docker-compose`.
*   **Resolution:** Use the modern `docker compose` (space) command, which is integrated into the main Docker CLI.

### pyproject.toml Dev Dependencies
*   **Issue:** The `[tool.uv.dev-dependencies]` table in `pyproject.toml` is deprecated.
*   **Symptom:** A warning is issued during `uv sync`.
*   **Resolution:** Moved the dev dependencies to the standard `[project.optional-dependencies]` table under the `dev` group. This aligns with PEP 621, making the project configuration tool-agnostic. Dev dependencies can now be installed locally with `uv sync --with-dev`.

### Docker Entrypoint vs Command
*   **Issue:** The `Dockerfile` defined an `ENTRYPOINT` for the CLI application (`python -m video2mdnotes.main`). When adding the `api` service in `docker-compose.yml`, setting `command: ["uvicorn", ...]` resulted in Docker appending the command to the entrypoint, causing a failure.
*   **Symptom:** `Usage: python -m video2mdnotes.main [OPTIONS] URL ... Error: No such option: --host`
*   **Resolution:** Explicitly set `entrypoint: ["uvicorn", ...]` in the `docker-compose.yml` for the `api` service to override the Dockerfile's default entrypoint.

---

## Later Requirements (Future Phase)
*   **Chrome Extension:** Extract audio from streaming sites via Web Audio API.
*   **Cloud Deployment:** Deploy to Cloud Run / AWS ECS.
