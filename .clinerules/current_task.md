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
*   **Result:** [COMPLETE]

### 2. Module: Downloader (yt-dlp wrapper)
*   **Goal:** Replace manual yt-dlp commands and clean_dir_filenames.sh.
*   **Result:** [COMPLETE]

### 3. Module: Transcriber (faster-whisper wrapper)
*   **Goal:** Port transcribe_dir.py into the modular architecture.
*   **Result:** [COMPLETE]

### 4. Module: Summarizer (litellm integration)
*   **Goal:** Replace batch_run.sh with a robust Python module.
*   **Result:** [COMPLETE]

### 5. Module: Orchestrator & CLI
*   **Goal:** Tie it all together into a single command and define the output logic.
*   **Result:** [COMPLETE]

### 6. Dockerization (Local)
*   **Goal:** Run the CLI inside a container.
*   **Result:** [COMPLETE]

### 7. Enhancement: Add Deno to Docker Image
*   **Goal:** Make yt-dlp more robust by providing a JavaScript runtime.
*   **Result:** [COMPLETE]

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
    *   (Pending)

---

## Side Quests, Errors & Learnings

### Typer Single-Command Behavior
*   **Issue:** When a `typer` application has only one command, Typer treats it as the "main" entry point.
*   **Symptom:** Invoking `runner.invoke(app, ["process", url])` fails with exit code 2 (Usage Error) because Typer expects `runner.invoke(app, [url])`.
*   **Resolution:** Adjusted the test invocation to match Typer's single-command behavior.

### Docker Compose V2 Command
*   **Issue:** The `docker-compose` (hyphenated) command is deprecated.
*   **Symptom:** `zsh: command not found: docker-compose`.
*   **Resolution:** Use the modern `docker compose` (space) command.

### pyproject.toml Dev Dependencies
*   **Issue:** The `[tool.uv.dev-dependencies]` table is deprecated.
*   **Symptom:** A warning is issued during `uv sync`.
*   **Resolution:** Moved dev dependencies to the standard `[project.optional-dependencies]` table.

---

## Later Requirements (Future Phase)
*   **FastAPI Implementation:** Expose endpoints for URL and File processing.
*   **Chrome Extension:** Extract audio from streaming sites via Web Audio API.
*   **Cloud Deployment:** Deploy to Cloud Run / AWS ECS.
