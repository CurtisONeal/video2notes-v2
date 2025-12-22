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
*   **Steps:**
    1.  Initialize pyproject.toml with dependencies (faster-whisper, yt-dlp, rich, pydantic-settings, litellm).
    2.  Create src/video2mdnotes/ package structure.
    3.  Create config.py to load settings (Paths, API Keys, Model preferences).
*   **Test:**
    *   uv sync installs successfully.
    *   pytest can import the package and load the configuration.

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
    *   This module will only support URLs that yt-dlp can handle directly (e.g., YouTube, Vimeo) or with simple cookie-based authentication.
    *   It will **not** support complex streaming sites (like mygreatlearning.com) that require JavaScript execution to discover stream manifests. This will be handled in a future phase by a browser extension.
*   **Steps:**
    1.  Implement downloader.py class/functions.
    2.  Integrate clean_filename logic.
*   **Test:**
    *   Unit: Test filename sanitizer with various inputs.
    *   Integration: Download a small test video from YouTube and verify .wav exists and plays.

### 3. Module: Transcriber (faster-whisper wrapper)
*   **Goal:** Port transcribe_dir.py into the modular architecture.
*   **Architecture:**
    *   Input: Path to .wav file.
    *   Output: Path to raw transcript (Markdown/Text) and segments data.
    *   Logic:
        *   Load model (cached).
        *   Transcribe with progress bar (Rich).
        *   Return structured transcript object.
*   **Steps:**
    1.  Refactor transcribe_dir.py into transcriber.py.
    2.  Ensure model path is configurable (for Docker volume mapping).
*   **Test:**
    *   Unit: Mock the WhisperModel to test segment handling logic.
    *   Integration: Run transcriber on a committed sample.wav file. Verify output text matches expected content.

### 4. Module: Summarizer (litellm integration)
*   **Goal:** Replace batch_run.sh with a robust Python module.
*   **Architecture:**
    *   Input: Transcript text/file.
    *   Output: Summary Markdown file.
    *   Logic:
        *   Use litellm for multi-provider LLM calls.
        *   Construct prompt using summarize_prompt.txt.
        *   Call LLM and save result.
*   **Steps:**
    1.  Implement summarizer.py using litellm.
    2.  Ensure prompt template is loaded from config/file.
*   **Test:**
    *   Unit: Mock the litellm.completion call.
    *   Integration: Send a short, fixed string to the actual LLM API and verify a response is received.

### 5. Module: Orchestrator & CLI
*   **Goal:** Tie it all together into a single command and define the output logic.
*   **Architecture:**
    *   Command: video2mdnotes process <URL>
    *   Output Modes:
        *   **Local (default):** Saves all artifacts to previous_run_results/{project}/.
        *   **Cloud:** Returns a ResultObject (Pydantic model) with transcript and summary text.
    *   Logic:
        1.  Call Downloader -> Get WAV + Metadata.
        2.  Call Transcriber -> Get Transcript.
        3.  Call Summarizer -> Get Summary.
        4.  Handle output based on mode (save locally or return object).
        5.  Clean up temporary files (e.g., the source WAV).
*   **Steps:**
    1.  Implement main.py with typer or argparse.
    2.  Implement the "Project-Based Archiving" logic.
*   **Test (End-to-End):**
    *   Create tests/e2e/test_full_pipeline.py.
    *   This test will run the full video2mdnotes process <URL> command on a stable, short YouTube video.
    *   It will verify that the final archive directory is created correctly and contains all expected artifacts. This is the "real test" that ensures all modules work together.

### 6. Dockerization (Local)
*   **Goal:** Run the CLI inside a container.
*   **Architecture:**
    *   Dockerfile using multi-stage build (uv for install).
    *   Volumes for: Output data (previous_run_results), Model cache (/root/.cache), Config (.env file).
*   **Steps:**
    1.  Write Dockerfile.
    2.  Write docker-compose.yml.
*   **Test:**
    *   docker-compose run app process <URL> works successfully and writes output to the host machine via the volume.

---

## Later Requirements (Future Phase)
*   **FastAPI Implementation:**
    *   Expose the Orchestrator via REST endpoints.
    *   POST /v1/process_url (takes a URL, runs the full pipeline).
    *   POST /v1/process_upload (takes an audio file blob, skips download, and feeds it to the transcriber).
*   **Chrome Extension:**
    *   A browser extension that can extract audio from complex streaming sites using the Web Audio API.
    *   The extension will call the POST /v1/process_upload endpoint on the FastAPI backend.
*   **Cloud Deployment:** Deploy Docker container to Cloud Run / AWS ECS.
*   **Cloud Storage:** Replace local file storage with S3/GCS.
