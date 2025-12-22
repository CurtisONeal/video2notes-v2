# Video2MDNotes User Guide (Python Application)

This guide describes how to use the modern, containerized Python application. This is the recommended way to run the project.

## 1. Initial Dependencies
To run the project, you only need one dependency installed on your local machine:
*   **Docker:** Docker Desktop (for Mac/Windows) or Docker Engine (for Linux) must be installed and running. All other dependencies (Python, ffmpeg, etc.) are handled inside the container.

## 2. Environment Variables (`.env` file)
Create a file named `.env` in the project root.

### Required Elements
You must provide an API key for the LLM you intend to use.
*   `OPENAI_API_KEY="sk-..."` (If using an OpenAI model)
*   `ANTHROPIC_API_KEY="sk-..."` (If using an Anthropic model)

### Optional Elements
These have sensible defaults but can be overridden.
*   `LLM_MODEL="gpt-4o-mini"` (Change to any model supported by your provider, e.g., "claude-3-haiku-20240307")
*   `FW_MODEL="medium"` (Whisper model size: "tiny", "base", "small", "medium", "large-v3")
*   `FW_COMPUTE="auto"` (Compute type for Whisper. "auto" correctly selects "float16" for Apple Silicon and "int8" for others)

## 3. Commands

### Build the Container
This only needs to be done once, or whenever you change the Python code or dependencies.
```bash
docker compose build
```

### Run the Pipeline
This is the main command to process a video.
```bash
docker compose run --rm app "YOUR_VIDEO_URL"
```

### Run with Options
You can pass CLI options after the URL.
```bash
# Don't keep the WAV file in the final archive
docker compose run --rm app "YOUR_VIDEO_URL" --no-keep-wav
```

### Get Help
To see all available commands and options:
```bash
docker compose run --rm app --help
```

## 4. Expected Results
After a successful run, a new directory will be created in `previous_run_results/`. The structure will be:
```
previous_run_results/
  └── YYYYMMDD_video_title/
      ├── original_url.txt
      ├── summaries/
      │   └── video_title.summary.md
      ├── transcripts/
      │   └── video_title.md
      └── wav_files/
          └── YYYYMMDD_video_title.wav
```
The output is automatically organized into a self-contained project folder.

## 5. Error Handling & Logs

### Error Display
If an error occurs (e.g., download fails, API key is invalid), the application will stop and print a red error message to your terminal.
```
2025-12-22 06:00:00 | ERROR    | __main__:process:100 - Processing failed: [Error Message]
```

### Log Files
The application currently logs directly to your terminal (stderr). There are no persistent log files created by default, but this can be enabled in `src/video2mdnotes/logger.py` if needed.

## 6. Other Questions

### Orphaned Code & Directories
*   **Yes, `wav_files_transcribed/` is now an orphaned legacy directory.** The new Python application does not use it. The old scripts (`transcribe_dir.sh`, `batch_run.sh`) are also orphaned and no longer part of the main workflow.
*   The new application uses a temporary directory (`temp_files/` by default, though this is handled inside the container) which is cleaned up after each run.

### Using the Original Scripts
*   **Yes, it is still possible.** As long as you have the local dependencies listed in the `Original_Script_based_User_Guide.md` installed on your machine (e.g., `pip install llm faster-whisper`), you can still run the old `.sh` and `.py` scripts manually. They do not conflict with the new application.

### Cleanup Commands
*   The new application **automatically cleans up** its temporary files. The final output is moved to the `previous_run_results` directory.
*   There are no dedicated commands to clean the `previous_run_results` directory; this is left to the user to manage.

### Local vs. Cloud Configuration
*   **No, there is not currently a setting for this.** The application is designed with a "Cloud-ready" architecture (returning Pydantic objects), but the CLI entrypoint (`main.py`) is hardcoded to the "Local" mode (saving files to disk).
*   Activating the "Cloud" mode would be the first step in the next phase of development (FastAPI implementation), where the API endpoint would call the core logic and return the result as JSON instead of saving it.
