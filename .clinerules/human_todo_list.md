# Video2MDNotes - Comprehensive Task List

Based on the project requirements and current code, here's your actionable task list to transform the loose scripts into the unified video2mdnotes application using __uv__ and __pyproject.toml__:

---

## 📋 PHASE 0: Git & Cleanup (Do First!)

### Git Repository Management

- [ ] __Review and commit staged changes__

  - Staged: `.clinerules/ClineRules.txt`, `clean_dir_filenames.sh`
  - Deleted: `vertex_intro_class/010___introduction_to_colab_enterprise_on_vertex_ai.wav`
  - Action: `git commit -m "Add Cline rules and clean_dir script"`

- [ ] __Clean up old test files from vertex_intro_class/__

  - Delete entire `vertex_intro_class/` directory (36+ deleted files showing in git status)
  - These are old test files no longer needed
  - Action: `rm -rf vertex_intro_class/` then `git add -u`

- [ ] __Add untracked files__

  - Add `.clinerules/Proj_requirements.md` (this requirements doc)
  - Evaluate `yt-dlp.textClipping` - delete if not needed
  - Action: `git add .clinerules/Proj_requirements.md`

- [ ] __Review and stage modified files__

  - `.gitignore`, `readme.md`, `summarize_prompt.txt`, `.DS_Store`
  - Review changes and commit: `git commit -m "Update documentation and configuration"`

- [ ] __Clean WAV files from project root__

  - Check for any `.wav` files in root directory
  - Move to archive or delete based on status
  - Action: `find . -maxdepth 1 -name "*.wav" -type f`

---

## 📦 PHASE 1: Dependency Management Migration (uv + pyproject.toml)

### Switch from venv to uv

- [ ] __Install uv__ (if not already installed)

  - macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Or: `brew install uv`

- [ ] __Create pyproject.toml__

  - Define project metadata (name, version, description, authors)
  - Add dependencies: `faster-whisper`, `yt-dlp`, `rich`, `fastapi`, `uvicorn`, `python-dotenv`
  - Add dev-dependencies: `pytest`, `ruff`
  - Set Python version requirement: `>=3.10`

- [ ] __Initialize uv project__

  - Run: `uv init` (if needed) or manually create pyproject.toml
  - Run: `uv sync` to create virtual environment and install dependencies

- [ ] __Update .gitignore__

  - Add `.venv/` (uv default virtual environment)
  - Add `__pycache__/`, `*.pyc`, `.env`
  - Add `.ruff_cache/`
  - Keep `.DS_Store` ignored

- [ ] __Remove old venv artifacts__

  - Delete old `.venv` directory if present
  - Update documentation to reference `uv run` instead of `python3`

---

## ⚙️ PHASE 2: Configuration Management

### Create .env file

- [ ] __Create .env template__

  - System configuration (SYSTEM_ARCH, SYSTEM_OS)
  - File management (AUDIO_ARCHIVE_DIR, AUDIO_DEFAULT_ACTION)
  - faster-whisper settings (FW_MODEL, FW_LANG, FW_COMPUTE, FW_BEAM, FW_VAD)
  - LLM provider config (LLM_PROVIDER, LLM_MODEL)
  - API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)
  - Web UI settings (WEB_HOST, WEB_PORT, WEB_ENABLE)
  - Cookie config (YT_DLP_BROWSER)

- [ ] __Create .env.example__

  - Copy .env structure with placeholder values
  - Add comments explaining each variable
  - Include in git repo (but not .env itself)

- [ ] __Add architecture detection module__

  - Create `src/utils.py` with `detect_system()` function
  - Auto-detect macOS Intel vs Apple Silicon
  - Set appropriate compute types (float16 for Apple Silicon, int8 for Intel)

---

## 🏗️ PHASE 3: Project Structure Refactoring

### Create src/ directory structure

- [ ] __Create directory layout__

  ```javascript
  src/
  ├── __init__.py
  ├── main.py           # CLI entry point
  ├── api.py            # FastAPI application
  ├── downloader.py     # yt-dlp wrapper
  ├── transcriber.py    # faster-whisper wrapper
  ├── summarizer.py     # LLM integration
  └── utils.py          # Shared utilities
  ```

- [ ] __Move and refactor transcribe_dir.py__

  - Migrate code to `src/transcriber.py`
  - Convert to modular functions
  - Add type hints to all functions
  - Update to use .env configuration

- [ ] __Create downloader.py__

  - Wrap yt-dlp functionality
  - Support single video and playlist URLs
  - Implement browser cookie authentication
  - Add filename normalization (integrate clean_dir_filenames.sh logic)
  - Return download metadata

- [ ] __Create summarizer.py__

  - Support multiple LLM providers (OpenAI, Anthropic, Ollama, llm CLI)
  - Load custom prompt from `config/summarize_prompt.txt`
  - Implement structured output generation
  - Append full transcript to summary
  - Handle API errors gracefully

- [ ] __Create main.py (CLI)__

  - Unified command-line interface
  - Argument parsing for URL/playlist input
  - Interactive user confirmations
  - Progress indicators with rich library
  - Orchestrate full pipeline

- [ ] __Create utils.py__

  - System/architecture detection
  - File operations (move, archive, delete)
  - Config loading from .env
  - Logging setup

---

## 🖥️ PHASE 4: User Interaction & File Lifecycle

### Add confirmation points

- [ ] __Post-download preview__

  - List downloaded audio files with metadata
  - Display file size, duration
  - Prompt: "Proceed with transcription? (y/n/retry)"
  - Option to play audio file for verification

- [ ] __Post-summarization review__

  - Display generated summary path
  - Prompt: "Open summaries for review? (y/n)"
  - Prompt: "Satisfied with summaries? (y/n/edit)"

- [ ] __Audio file disposal__

  - Prompt: "What to do with audio files? (delete/archive/keep)"
  - Implement archive functionality (move to configured directory)
  - Respect AUDIO_DEFAULT_ACTION config
  - Support batch operations for multiple files

### Implement file lifecycle

- [ ] __Update directory structure__

  - Create `downloads/` for temporary audio
  - Keep `transcripts/` for temporary transcripts
  - Keep `summaries/` for final notes
  - Create `archive/` for saved audio files (optional)

- [ ] __Auto-delete transcripts__

  - After appending to summary, delete transcript file
  - Log deletion for user awareness
  - Ensure transcript content preserved in summary

- [ ] __Enhance batch_run.sh or migrate to Python__

  - Consider replacing bash script with Python equivalent
  - Better error handling and progress tracking
  - Integration with src/summarizer.py

---

## 🌐 PHASE 5: Web Interface (FastAPI)

### Create API backend

- [ ] __Create src/api.py__

  - FastAPI application setup
  - CORS configuration for local development
  - Static file serving for frontend

- [ ] __Implement API endpoints__

  - POST `/submit` - Submit video URL for processing
  - GET `/status/{job_id}` - Check processing status
  - GET `/downloads` - List downloaded audio files
  - GET `/transcripts` - List transcript files
  - GET `/summaries` - List summary files
  - GET `/preview/{file_type}/{filename}` - Preview file content
  - POST `/config` - Update configuration
  - DELETE `/cleanup/{file_type}/{filename}` - Delete specific file

- [ ] __Add background task processing__

  - Use FastAPI BackgroundTasks for async processing
  - Or integrate with Celery for production
  - Track job status in memory (later: database)

- [ ] __Create simple frontend__

  - HTML templates for UI
  - URL submission form
  - Processing status monitor
  - File browser with preview
  - Audio player integration
  - Markdown preview

---

## 🐳 PHASE 6: Containerization (Docker)

### Create Docker setup

- [ ] __Create Dockerfile__

  - Base image: Python 3.11+ slim
  - Install system dependencies (ffmpeg for audio processing)
  - Copy application code
  - Install Python dependencies with uv
  - Download faster-whisper models
  - Expose port 8000
  - Set entrypoint

- [ ] __Create docker-compose.yml__

  - Define app service
  - Volume mounts for persistence (models, downloads, summaries)
  - Environment variable configuration
  - Port mapping (8000:8000)
  - Optional: Redis service for caching

- [ ] __Add .dockerignore__

  - Exclude `.venv/`, `__pycache__/`, `.git/`
  - Exclude large model cache (download in container)
  - Exclude test files and documentation

- [ ] __Test Docker build__

  - Build image: `docker build -t video2mdnotes .`
  - Run container: `docker-compose up`
  - Verify web UI accessible at [](http://localhost:8000)<http://localhost:8000>
  - Test end-to-end workflow in container

---

## 📚 PHASE 7: Documentation

### Create comprehensive docs

- [ ] __Update README.md__

  - Project overview and features
  - Installation instructions (uv + Docker)
  - Quick start guide
  - Configuration reference
  - Usage examples
  - Troubleshooting section

- [ ] __Create docs/setup.md__

  - Detailed setup for each platform (macOS, Windows, Linux)
  - uv installation and initialization
  - API key setup for LLM providers
  - Browser cookie extraction guide
  - Model selection recommendations by hardware

- [ ] __Create docs/usage.md__

  - CLI usage examples
  - Web UI walkthrough
  - Playlist processing tips
  - Batch processing strategies
  - File management best practices

- [ ] __Create docs/api.md__

  - FastAPI endpoint documentation
  - Request/response examples
  - Error codes and handling
  - Authentication (if added later)

- [ ] __Add inline documentation__

  - Google-style docstrings for all functions
  - Type hints throughout codebase
  - Comments for complex logic

---

## 🧪 PHASE 8: Testing & Quality

### Add tests

- [ ] __Create tests/ directory__

  - `tests/test_downloader.py`
  - `tests/test_transcriber.py`
  - `tests/test_summarizer.py`
  - `tests/test_utils.py`
  - `tests/test_api.py`

- [ ] __Create test fixtures__

  - Sample audio files (short clips)
  - Mock transcripts
  - Mock LLM responses
  - Configuration templates

- [ ] __Configure pytest__

  - Add pytest configuration in pyproject.toml
  - Setup coverage reporting
  - Configure test discovery

- [ ] __Add code quality tools__

  - Ruff for linting and formatting
  - Pre-commit hooks (optional)
  - GitHub Actions for CI (optional)

---

## 🎯 PHASE 9: Polish & Release

### Final touches

- [ ] __Test cross-platform__

  - macOS Intel
  - macOS Apple Silicon
  - Windows with WSL2
  - Linux (Ubuntu/Debian)

- [ ] __Performance optimization__

  - Profile transcription speed
  - Optimize concurrent processing
  - Test with various model sizes
  - Document performance benchmarks

- [ ] __Create release checklist__

  - Version tagging (v0.1.0)
  - GitHub release with binaries
  - Change log
  - Migration guide from scripts

- [ ] __Security audit__

  - Review API key handling
  - Verify .env not committed
  - Check file permission handling
  - Validate user input sanitization

---

## 🚀 FUTURE ENHANCEMENTS (Post-MVP)

### Phase 2 Features (Optional)

- [ ] Chrome extension for one-click processing
- [ ] Obsidian plugin integration
- [ ] Advanced summarization (multi-pass, concept mapping)
- [ ] Speaker diarization
- [ ] Automatic chapter detection
- [ ] Database for job tracking (PostgreSQL/SQLite)
- [ ] User authentication and multi-user support

---

## Current Status Summary

__✅ What you have:__

- Basic transcription script (transcribe_dir.py)
- Filename cleaning utility (clean_dir_filenames.sh)
- Batch summarization script (batch_run.sh)
- Working workflow (manual steps)

__🔧 What needs immediate attention:__

1. Git cleanup (commit/delete old vertex_intro_class files)
2. Clean any stray .wav files in root
3. Migrate to uv + pyproject.toml
4. Create .env configuration
5. Refactor into src/ structure

__📝 Recommendation:__ Start with __Phase 0__ (Git cleanup) and __Phase 1__ (uv migration) first, then move to __Phase 2__ (configuration) and __Phase 3__ (structure refactoring). The web UI (Phase 5) and Docker (Phase 6) can come after the core CLI is solid.

Would you like me to help implement any specific phase? Or should I prioritize certain tasks differently based on your immediate needs?

Auto-approve:Read, Safe Commands, MCP
