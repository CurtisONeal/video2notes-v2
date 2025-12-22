# Video2MDNotes - Project Requirements

## 1. Project Overview

### Vision
Create a unified, automated pipeline that transforms online video content into structured Markdown notes optimized for technical learning and reference. The system should handle everything from video URL input to final formatted notes with minimal manual intervention.

### Target Users
- Data engineers and data scientists
- Software developers (Python, Bash, C++ backgrounds)
- Technical learners who need command reference and concept summaries
- Users who consume video courses, tutorials, and technical presentations

### Core Value Proposition
Transform hours of video content into searchable, reference-ready Markdown notes that capture:
- Key concepts and learning objectives
- Command syntax and code examples
- New vocabulary and technical terms
- Visual UI elements requiring screenshot reference
- Full timestamped transcripts for detailed lookup

---

## 2. Functional Requirements

### 2.1 Video Download & Authentication
- **Download audio from video URLs** using yt-dlp
- **Browser cookie authentication** to access protected content (courses, private videos)
- **Playlist support**: Process single videos or entire playlists automatically
- **Format**: Extract audio-only in WAV format for transcription
- **Cookie sources**: Support Chrome, Firefox, Safari browser cookies

### 2.2 Filename Normalization
- **Automatic filename cleaning** to ensure compatibility across platforms
- **Transformations applied**:
  - Replace dashes and spaces with underscores
  - Add ISO date prefix (YYYYMMDD_)
  - Convert to lowercase
  - Remove special characters
  - Preserve file extensions

### 2.3 Audio Transcription
- **Speech-to-text** using faster-whisper (local, offline processing)
- **Timestamped output** with segments marked by start time
- **Multi-language support** with primary focus on English
- **VAD (Voice Activity Detection)** to filter silence
- **Configurable models**: small, medium, large-v3
- **Hardware optimization**: Auto-detect architecture for compute type

### 2.4 AI-Powered Summarization
- **Multi-provider LLM support**:
  - OpenAI API (GPT-4, GPT-4o-mini)
  - Anthropic API (Claude)
  - Ollama (local models)
  - Simon Willison's llm CLI
- **Custom prompt system** for structured output generation
- **Structured sections**:
  - Summary (5-10 key points)
  - New Commands (CLI, code snippets)
  - New Vocabulary (terms and definitions)
  - UI Call-Outs (visual elements needing screenshots)
  - Special Attention (complex steps)
  - Full Transcript (appended for reference)

### 2.5 User Interaction & File Management
- **Preview downloaded audio** before processing
- **User confirmation points**:
  1. After download: Confirm audio quality and usability
  2. After summarization: Review generated notes
  3. Audio disposal: Choose delete or archive
- **Automatic transcript cleanup**: Delete transcript files after appending to summaries
- **Configurable audio archiving**:
  - Default action: prompt, delete, or archive
  - Archive location: user-specified or ~/Downloads
  - Per-file or batch decisions

### 2.6 File Preview Capabilities
- **Web UI preview**:
  - In-browser audio player
  - Markdown preview of transcripts and summaries
  - Metadata display (duration, file size, processing status)
- **CLI preview**:
  - File listing with metadata
  - Audio playback command suggestions
  - Quick content inspection

---

## 3. Technical Stack

### 3.1 Core Technologies
- **Python**: >=3.10 (primary language)
- **Bash**: Script orchestration and system commands
- **yt-dlp**: Video/audio downloading
- **faster-whisper**: Local speech-to-text transcription
- **LLM Providers**: OpenAI, Anthropic, Ollama, llm CLI

### 3.2 Dependency Management
- **uv**: Astral's fast Python package manager
- **pyproject.toml**: Project configuration and dependencies
- **No legacy tools**: No pip, poetry, or requirements.txt

### 3.3 Python Dependencies
```toml
[project]
dependencies = [
    "faster-whisper>=1.0.0",
    "yt-dlp>=2024.0.0",
    "rich>=13.0.0",
    "fastapi>=0.110.0",
    "uvicorn>=0.27.0",
    "python-dotenv>=1.0.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "ruff>=0.2.0",
]
```

### 3.4 Containerization
- **Docker**: Primary deployment method
- **docker-compose**: Multi-container orchestration
- **Benefits**:
  - Cross-platform consistency
  - Isolated environment
  - Easy setup and deployment
  - Model caching in volumes

### 3.5 Web Interface
- **FastAPI**: Backend REST API
- **Uvicorn**: ASGI server
- **Local access**: http://localhost:8000
- **Features**:
  - URL submission
  - Processing status monitoring
  - File preview and download
  - Configuration management

---

## 4. Cross-Platform Support

### 4.1 Supported Platforms
- **macOS**: Intel (x86_64) and Apple Silicon (ARM64/M1/M2/M3)
- **Windows**: x86_64 with WSL2 or native Docker Desktop
- **Linux**: x86_64 and ARM64

### 4.2 Architecture Detection
- **Automatic detection** of system and CPU architecture
- **Manual override** via .env configuration
- **Optimized compute types** per architecture:
  - Apple Silicon: `float16`
  - Intel CPU: `int8`
  - High-performance: `int8_float16`

### 4.3 Detection Logic
```python
import platform

def detect_system():
    """Auto-detect system OS and architecture"""
    system = platform.system().lower()  # darwin, linux, windows
    machine = platform.machine().lower()  # x86_64, arm64, aarch64
    
    if system == 'darwin':
        if 'arm' in machine or 'aarch' in machine:
            return 'macos', 'apple_silicon', 'float16'
        else:
            return 'macos', 'x86_64', 'int8'
    elif system == 'windows':
        return 'windows', machine, 'int8'
    else:  # linux
        return 'linux', machine, 'int8'
```

---

## 5. Configuration Management

### 5.1 Environment Variables (.env)
```env
# System Configuration (auto-detect or manual override)
SYSTEM_ARCH=auto              # auto | x86_64 | arm64 | apple_silicon
SYSTEM_OS=auto                # auto | macos | windows | linux

# File Management
AUDIO_ARCHIVE_DIR=~/Downloads # Archive location for audio files
AUDIO_DEFAULT_ACTION=prompt   # prompt | delete | archive
KEEP_TRANSCRIPTS=false        # Delete transcripts after summarization

# faster-whisper Configuration
FW_MODEL=medium               # tiny | base | small | medium | large-v3
FW_LANG=en                    # Language code (ISO 639-1)
FW_COMPUTE=auto               # auto | int8 | float16 | int8_float16
FW_BEAM=1                     # Beam size for transcription
FW_VAD=true                   # Enable Voice Activity Detection
FW_CHUNK=30                   # Chunk length in seconds
FW_WORD_TIMESTAMPS=false      # Enable word-level timestamps

# LLM Provider Configuration
LLM_PROVIDER=openai           # openai | anthropic | ollama | llm_cli
LLM_MODEL=gpt-4o-mini         # Model name for chosen provider

# API Keys (cloud providers only)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Ollama Configuration (local LLM)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Web UI Configuration
WEB_HOST=localhost
WEB_PORT=8000
WEB_ENABLE=true               # Enable web interface

# Cookie Configuration (yt-dlp)
YT_DLP_BROWSER=chrome         # chrome | firefox | safari
```

### 5.2 Model Storage
- **faster-whisper models**: `~/.cache/huggingface/hub/` (default)
- **Custom location**: Set via environment variable
- **Docker volumes**: Persist model cache between container restarts
- **Size estimates**:
  - tiny: ~75 MB
  - base: ~150 MB
  - small: ~500 MB
  - medium: ~1.5 GB
  - large-v3: ~3 GB

### 5.3 Recommended Models by Hardware
- **Apple Silicon (M1/M2/M3)**: medium with float16
- **Intel CPU (8GB RAM)**: small with int8
- **Intel CPU (16GB+ RAM)**: medium with int8
- **High-performance systems**: large-v3 with int8_float16

---

## 6. Directory Structure

### 6.1 Project Layout
```
video2mdnotes/
├── .clinerules/
│   ├── ClineRules.txt
│   └── Proj_requirements.md (this file)
├── .env                      # Configuration
├── pyproject.toml            # Project dependencies
├── docker-compose.yml        # Container orchestration
├── Dockerfile               # Container definition
│
├── src/                     # Source code (future unified app)
│   ├── __init__.py
│   ├── main.py             # CLI entry point
│   ├── api.py              # FastAPI application
│   ├── downloader.py       # yt-dlp wrapper
│   ├── transcriber.py      # faster-whisper wrapper
│   ├── summarizer.py       # LLM integration
│   └── utils.py            # Shared utilities
│
├── config/
│   └── summarize_prompt.txt # LLM prompt template
│
├── downloads/               # Temporary: Downloaded audio
├── transcripts/             # Temporary: Auto-deleted after summarization
├── summaries/               # Persistent: Final structured notes
├── archive/                 # Optional: Archived audio files
│
├── tests/                   # Unit and integration tests
│
└── docs/                    # Documentation
    ├── setup.md
    ├── usage.md
    └── api.md
```

### 6.2 File Lifecycle
```
1. URL → downloads/*.wav           [User previews and confirms]
2. downloads/*.wav → transcripts/*.md
3. transcripts/*.md → summaries/*.md (transcript appended)
4. DELETE transcripts/*.md         [Automatic]
5. downloads/*.wav → archive/ OR DELETE [User chooses]
```

---

## 7. Processing Pipeline

### 7.1 Complete Workflow

```
┌─────────────────────────────────────────────────────────┐
│  1. INPUT: Video URL or Playlist                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  2. DOWNLOAD (yt-dlp)                                   │
│     - Extract audio as WAV                              │
│     - Apply filename normalization                      │
│     - Save to downloads/                                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  3. PREVIEW & CONFIRM                                   │
│     - Display file list with metadata                   │
│     - Audio player (web UI) or playback commands (CLI)  │
│     - User confirms: proceed, retry, or cancel          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  4. TRANSCRIBE (faster-whisper)                         │
│     - Process downloads/*.wav                           │
│     - Generate timestamped Markdown                     │
│     - Save to transcripts/                              │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  5. SUMMARIZE (LLM)                                     │
│     - Load custom prompt template                       │
│     - Process each transcript                           │
│     - Generate structured summary                       │
│     - Append full transcript to summary                 │
│     - Save to summaries/                                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  6. CLEANUP TRANSCRIPTS                                 │
│     - Auto-delete transcripts/ files                    │
│     - (Content preserved in summaries/)                 │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  7. REVIEW SUMMARIES                                    │
│     - User reviews generated notes                      │
│     - Open in browser/editor                            │
│     - Confirm satisfaction                              │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  8. AUDIO DISPOSAL                                      │
│     - User choice: DELETE or ARCHIVE                    │
│     - If ARCHIVE: move to configured directory          │
│     - If DELETE: remove from downloads/                 │
│     - Default action configurable in .env               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  9. COMPLETE                                            │
│     - summaries/ contains final notes                   │
│     - archive/ contains saved audio (optional)          │
│     - Ready for export to Obsidian or other tools       │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Batch Processing (Playlists)
- **Detection**: Automatically identifies playlist URLs
- **Processing**: Sequential download and transcription
- **Confirmation points**:
  - Option 1: Per-video confirmations (slower, more control)
  - Option 2: Per-batch confirmations (faster, batch operations)
  - Configurable via .env: `BATCH_CONFIRM=per_video` or `per_batch`
- **Error handling**: Continue on failure, report at end

### 7.3 Error Recovery
- **Download failures**: Retry with exponential backoff
- **Transcription failures**: Skip file, log error, continue
- **Summarization failures**: Preserve transcript, retry with different model
- **User abort**: Save progress, allow resume from checkpoint

---

## 8. User Interface Requirements

### 8.1 Command-Line Interface (Primary)

#### Installation
```bash
# Clone repository
git clone <repository-url>
cd video2mdnotes

# Install with uv
uv sync

# Or with Docker
docker-compose up --build
```

#### Basic Usage
```bash
# Process single video (CLI)
uv run python src/main.py --url "https://youtube.com/watch?v=..."

# Process playlist
uv run python src/main.py --playlist "https://youtube.com/playlist?list=..."

# With Docker
docker-compose run app --url "https://youtube.com/watch?v=..."
```

#### Interactive Commands
```bash
# Preview downloaded files
> Preview downloaded files? (y/n): y
  1. 20241119_video_lecture_part1.wav (45.2 MB, 24:15)
  2. 20241119_video_lecture_part2.wav (38.7 MB, 20:40)
> Play audio? Enter number or 'c' to continue: 1
  [Audio plays or command shown: afplay downloads/20241119_video_lecture_part1.wav]
> Proceed with transcription? (y/n/retry): y

# After summarization
> Open summaries for review? (y/n): y
  [Browser opens to http://localhost:8000/summaries]
> Satisfied with summaries? (y/n/edit): y

# Audio file management
> What to do with audio files? (delete/archive/keep): archive
  Moving 2 files to ~/Downloads/video2mdnotes_archive/
  ✓ Complete
```

### 8.2 Web Interface (Secondary)

#### Access
- **URL**: http://localhost:8000
- **Docker**: Automatically available when container running
- **Native**: Run `uvicorn src.api:app --reload`

#### Features

**Dashboard**
- Processing status overview
- Recent conversions
- Storage usage statistics

**URL Submission Page**
- Input field for video URL or playlist
- Browser cookie selector (Chrome/Firefox/Safari)
- Processing options (model selection, language)
- Submit and start processing

**Processing Monitor**
- Real-time progress indicators
- Current stage (downloading, transcribing, summarizing)
- Estimated time remaining
- Error notifications

**File Browser**
- Downloads: Preview audio files before processing
  - Inline audio player
  - File metadata (duration, size, format)
  - Delete or process controls
- Summaries: View generated notes
  - Markdown preview
  - Download as .md file
  - Edit and re-save
  - Export to Obsidian/Notion

**Configuration Panel**
- Edit .env variables via web form
- Model selection and testing
- LLM provider setup and API key management
- Directory path configuration

### 8.3 Progress & Feedback

**CLI Output**
```
[1/4] Downloading audio from playlist (3 videos)...
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% (3/3)
[2/4] Transcribing audio files...
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  67% (2/3)
      Currently: video_lecture_part2.wav (03:45 / 20:40)
```

**Web UI Notifications**
- Toast notifications for status updates
- Error alerts with retry options
- Success confirmations with action buttons

---

## 9. Performance Requirements

### 9.1 Resource Requirements

**Minimum System**
- CPU: 2 cores (4 threads)
- RAM: 8 GB
- Storage: 10 GB free (5 GB for models + 5 GB for working files)
- Network: Stable connection for downloads and API calls

**Recommended System**
- CPU: 4+ cores (8+ threads)
- RAM: 16 GB
- Storage: 20 GB free
- GPU: Optional (faster-whisper supports CUDA)

**Docker Requirements**
- Docker Engine 20.10+
- Docker Compose 2.0+
- Allocated resources: 4 GB RAM minimum, 8 GB recommended

### 9.2 Processing Time Estimates

**Transcription** (faster-whisper on CPU)
- small model: ~20-30 seconds per minute of audio
- medium model: ~30-60 seconds per minute of audio
- large-v3 model: ~60-120 seconds per minute of audio

**Summarization** (depends on LLM provider)
- OpenAI API: ~5-15 seconds per transcript
- Anthropic API: ~5-15 seconds per transcript
- Ollama (local): ~30-120 seconds per transcript (depends on model)
- llm CLI: Variable (depends on configured backend)

**Total Pipeline**
- 10-minute video: ~5-15 minutes end-to-end
- 1-hour video: ~30-90 minutes end-to-end
- Primarily limited by transcription speed

### 9.3 Optimization Strategies
- **Parallel processing**: Multiple files transcribed concurrently
- **Batch API calls**: Group LLM requests where possible
- **Model caching**: Keep models in memory for sequential files
- **Incremental processing**: Resume from last checkpoint on failure

### 9.4 Performance Monitoring
- Processing time per stage logged
- Resource usage tracked (CPU, memory, disk)
- Bottleneck identification in logs
- Performance metrics in web UI

---

## 10. Security & Privacy

### 10.1 Data Handling
- **Local processing**: Transcription done locally (offline capable)
- **API calls**: Only summarization sent to external LLMs (if configured)
- **Credentials**: API keys in .env (never committed to git)
- **Cookie security**: Browser cookies extracted securely, not persisted

### 10.2 File Permissions
- **Audio files**: Restricted to user only
- **Transcripts**: Temporary, auto-deleted
- **Summaries**: User-owned files
- **Configuration**: .env with restricted permissions (600)

### 10.3 Network Security
- **HTTPS**: All API calls use encrypted connections
- **Local web UI**: Bound to localhost only (not exposed to network)
- **No telemetry**: No usage data collected or transmitted

---

## 11. Testing Requirements

### 11.1 Unit Tests
- Filename normalization functions
- Architecture detection logic
- Configuration loading and validation
- File operations (move, delete, archive)

### 11.2 Integration Tests
- End-to-end pipeline with sample audio
- Docker container builds and runs
- Web UI API endpoints
- LLM provider integrations (with mocks)

### 11.3 Platform Tests
- macOS Intel and Apple Silicon
- Windows with WSL2
- Linux (Ubuntu, Debian)

### 11.4 Test Fixtures
- Sample audio files (short clips)
- Mock transcripts
- Mock LLM responses
- Configuration templates

---

## 12. Future Enhancements

### 12.1 Phase 2 Features
- **Chrome Extension**
  - One-click processing from video page
  - Right-click menu integration
  - Progress notifications
  - Direct save to Obsidian vault

- **Obsidian Integration**
  - Plugin for importing notes
  - Auto-tagging based on content
  - Bidirectional linking
  - Template customization

- **Advanced Summarization**
  - Multi-pass summarization (overview → detailed)
  - Concept mapping and relationships
  - Automatic flashcard generation
  - Key frame extraction from video

### 12.2 Phase 3 Features
- **Collaboration**
  - Shared note repositories
  - Multi-user access
  - Review and comment system
  - Export to Notion, Confluence

- **AI Enhancements**
  - Speaker diarization (who said what)
  - Automatic chapter detection
  - Topic segmentation
  - Q&A generation for study

- **Platform Expansion**
  - Mobile app (iOS, Android)
  - Cloud deployment option
  - SaaS offering
  - API for third-party integration

### 12.3 Obsidian Integration Details
- **Export format**: Obsidian-compatible Markdown
- **Metadata**: YAML frontmatter with tags
- **Links**: Internal links for related notes
- **Media**: Embed referenced timestamps
- **Sync**: Auto-sync to vault directory

---

## 13. Quality Standards

### 13.1 Code Quality
- **PEP 8 compliance**: All Python code follows style guidelines
- **Type hints**: Full type annotations for functions
- **Docstrings**: Google-style docstrings for all public functions
- **Error handling**: Comprehensive try-except with logging
- **Linting**: Ruff for code quality checks

### 13.2 Documentation
- **README**: Setup, usage, troubleshooting
- **API docs**: Auto-generated from FastAPI
- **Architecture diagram**: Visual system overview
- **Example workflows**: Step-by-step tutorials
- **Change log**: Version history and migration guides

### 13.3 User Experience
- **Clear feedback**: Progress indicators for all operations
- **Helpful errors**: Actionable error messages with solutions
- **Consistent naming**: Predictable file and directory names
- **Minimal configuration**: Sensible defaults, optional customization

---

## 14. Success Metrics

### 14.1 Functional Success
- ✅ Successfully download and process single videos
- ✅ Successfully process entire playlists
- ✅ Generate accurate transcripts (>95% accuracy for clear audio)
- ✅ Generate well-structured summaries following prompt template
- ✅ Run on all supported platforms (macOS, Windows, Linux)

### 14.2 Performance Success
- ✅ Process 1-hour video in <90 minutes on recommended hardware
- ✅ Use <2 GB additional RAM during processing
- ✅ Docker container starts in <30 seconds
- ✅ Web UI responsive (<1 second page loads)

### 14.3 User Experience Success
- ✅ Setup completed in <15 minutes (including model download)
- ✅ Intuitive CLI with helpful prompts
- ✅ Web UI accessible to non-technical users
- ✅ Clear documentation answers common questions

### 14.4 Reliability Success
- ✅ Graceful error handling (no crashes)
- ✅ Resume capability after interruption
- ✅ Data integrity (no lost transcripts/summaries)
- ✅ Cross-platform consistency

---

## 15. Development Roadmap

### 15.1 Phase 1: MVP (Current → 4 weeks)
- Week 1: Unified CLI application
  - Integrate existing scripts
  - Add user confirmation points
  - Implement file lifecycle management
  
- Week 2: Configuration & Architecture
  - Implement .env configuration
  - Add architecture auto-detection
  - Create pyproject.toml with uv
  
- Week 3: Web UI (Basic)
  - FastAPI backend
  - URL submission page
  - Processing monitor
  - File browser
  
- Week 4: Docker & Documentation
  - Dockerfile and docker-compose
  - Cross-platform testing
  - README and setup guides
  - Initial release (v0.1.0)

### 15.2 Phase 2: Enhancement (Weeks 5-8)
- Week 5-6: Multi-LLM Support
  - Ollama integration
  - llm CLI integration
  - Provider switching in UI
  
- Week 7: Advanced Features
  - Batch processing optimizations
  - Resume from checkpoint
  - Performance monitoring
  
- Week 8: Polish & Release
  - Bug fixes
  - UI improvements
  - Documentation updates
  - Release v0.2.0

### 15.3 Phase 3: Extensions (Weeks 9-12)
- Obsidian plugin development
- Chrome extension
- Advanced summarization features
- Release v1.0.0

---

## 16. Appendix

### 16.1 Technologies Reference

**yt-dlp**
- Docs: https://github.com/yt-dlp/yt-dlp
- Cookie extraction: `--cookies-from-browser BROWSER`
- Audio extraction: `-x --audio-format wav`

**faster-whisper**
- Docs: https://github.com/guillaumekln/faster-whisper
- Models: https://huggingface.co/guillaumekln/faster-whisper
- Compute types by platform documented

**uv**
- Docs: https://docs.astral.sh/uv/
- Fast Python package manager by Astral
- Direct replacement for pip, poetry, pipenv

**Simon Willison's llm**
- Docs: https://llm.datasette.io/
- Multi-provider CLI tool
- Plugin system for extensibility

### 16.2 Glossary

- **VAD**: Voice Activity Detection - filters silence from audio
- **Beam size**: Search width for transcription (higher = slower but more accurate)
- **Compute type**: Quantization level for model inference (int8, float16, etc.)
- **Whisper**: OpenAI's speech recognition model
- **faster-whisper**: Optimized implementation using CTranslate2
- **uv**: Fast Python package installer and environment manager
- **pyproject.toml**: Python project configuration file (PEP 518)

### 16.3 File Format Specifications

**Transcript Format** (transcripts/*.md)
```markdown
---
title: "Video Title"
source: filename.wav
model: medium
language: en
generated_at: 2024-11-19T00:00:00
---

# Summary

_(Write your 5-bullet summary here.)_

# Notes

- [00:00:00.000] Transcript text segment one
- [00:00:15.342] Transcript text segment two
...
```

**Summary Format** (summaries/*.md)
```markdown
# Video Title, Date Recorded, URL

## Summary
- Key point 1
- Key point 2
...

## New Commands
- `command` - description

## New Vocabulary
- term - definition

## UI Call-Outs
- [HH:MM:SS] description

## Special Attention
### Complex Topic
- Sub-point 1
- Sub-point 2

## Transcript
(Full transcript appended here from transcripts/*.md)
```

---

## Document Revision History

- **v1.0** (2024-11-19): Initial comprehensive requirements document
  - Complete functional and technical specifications
  - Cross-platform support details
  - Interactive workflow with user confirmations
  - uv and pyproject.toml dependency management
  - Docker containerization approach
  - Web UI specifications
  - Future enhancement roadmap
