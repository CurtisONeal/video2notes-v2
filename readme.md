# Fast video notetaker v1

The point of this project is to have an initial python script that when provided the url of a video or video playslist that is shown in the current browser it will download the best version of the video's audio transcript and then use whiper to create text files, then use a prompt to summarize those using a local llm, or a foundational model API key.

# TODO 
1. Locate the original partial scripts [DONE]
2. Get it running 
3. Refactor the folder structure to modern python

## For To Do Contexts See:
0. /curtisoneal@Curtiss-MBP video2mdnotes  <-- symbolic link?
1. /Users/curtisoneal/video2mdnotes/readme.md
2. /Users/curtisoneal/video2mdnotes/results/vertex_intro_class/vertex_intro_url.txt
3. /Users/curtisoneal/video2mdnotes/yt-dlp.textClipping
4. /Users/curtisoneal/quick_tests/Video_ripper_pland_chatgpt.md
5. /usr/local/Cellar/yt-dlp

## Project Structure
```
langchain_rag_pilot/
 |----- .benchmarks            # ??
 |----- .venv/                 # Virtual environment directory
 |----- human_read_docs/        # Documentation
|    |----- archived_from_ai/   # stuff away from the  AI 
|    |-----.gitkeep    # Required for empty directories
|    |----- descriptive_video_transcribing_fast_iteration_loop.md
|    |----- review_yt-dlp_cli_commands_doc.md
|   +---- video_transcript_ripper_plan-chatgpt5_project_copy.md
 |----- documents/             # Files to be processed
|    |-----.gitkeep            # Required for empty directories
|    |----- excel/
|    |----- html_docs/
|    |----- images/             # png, jpg
|    |----- yellow-up_in_rag/
|    +---- 7 other pdfs
 |----- langchain_rag_pilot/     # Main package directory
|    |----- document_loaders.py  # Document loading and processing
|    |----- document_manager_interaction_tool.py  # Document loading and processing
|    |----- main.py              # Core functionality and context management
|    +---- __init__.py
 |----- tests/                   # Test suite
|    |----- fixtures/            # Test files
|    |----- conftest.py
|    |----- generate_fixtures.py
|    |----- test_document_loader.py
|    |----- test_main.py 
|    |----- test_main_copy.py
|    |----- test_ocr.py
|    +---- test_sample_loader.py
 |----- .coverage     
 |----- .env               # Your actual Environment variables - don't commit
 |----- .env.example             # Environment template variables
 |----- .gitignore               # Files to ignore when committing
 |----- .python-version          # Python version for Hatchling
 |----- Dockerfile               # TBD Container configuration
 |----- pyproject.toml           # Modern Python packaging with Hatchling
 |----- README.md                # Overview of the project
 |----- sources.db               # SQLite database for document tracking / management
 +---- uv.lock                  # uv versions locked file
```

### Package Management

This project uses modern Python packaging tools:
- **UV**: Fast, reliable package installer
- **Hatchling**: Build backend for modern Python packaging
- **pyproject.toml**: Single source of truth for project configuration

Key benefits:
- Faster package installation with UV
- Reproducible builds with Hatchling
- Clean dependency management
- Better Docker support
- Copes with a package's dependencies changing over time and a conflict in langchain packages

## Project Setup

### Prerequisites
- Python 3.11.7 (required)
- UV package manager (for fast, reliable package installation)
- OpenAI API key
- Homebrew (for Mac users)
- langchain_community’s unstructured loader calls LibreOffice to convert legacy .doc/.ppt to .docx/.pptx.
- uv pip install msoffcrypto-tool # import name is 'msoffcrypto' but the package is 'msoffcrypto-tool'

### Quick Start

### Clone the repository
```bash 
git clone <repository-url> 
cd langchain-rag-pilot
```

### Install Python 3.11.7 if needed (macOS)
`pyenv local 3.11.7`

# sanity check
`python --version`          # should report 3.11.7
`which python`              # should be a pyenv shim, e.g. ~/pyenv/shims/python

### Install system dependencies for PDF processing
`brew install qpdf`

### Install UV if not already installed
`curl -LsSf https://astral.sh/uv/install.sh | sh`

### Create a virtual environment with UV (uses Python 3.11.7 from pyproject.toml)
`uv venv --python 3.11.7`

### Activate virtual environment
`source .venv/bin/activate # On Windows: .venv\Scripts\activate`

### Install the package in development mode using UV
`uv pip install -e .`

1. Create .env file
`echo "OPENAI_API_KEY_PERS_LANGCHAIN=your-api-key" > .env`

2. Create required directories:
`mkdir -p data/documents chroma_db`

3. To RUN the application:
`python -m langchain_rag_pilot.main`

## Development Tools
To install and use the development tools, you'll need to install UV first:

## Install development dependencies
`uv pip install -e ".[dev]"`

## Run tests
`pytest tests/ -v` # V is verbose | Q is quiet

## Run linter
`ruff check .`

## Run type checker
`mypy langchain_rag_pilot/`

2. Create required directories:
`mkdir -p data/documents chroma_db`

## Document Management CLI
The system provides a command-line interface for managing your documents:

1. Query document chunks
`python -m langchain_rag_pilot.document_manager query --source "path/to/document.pdf"`

2. Delete documents from the database (not the directories) by source
`python -m langchain_rag_pilot.document_manager delete --source "path/to/document.pdf"`

### The document management system integrates with the Chroma vector store and provides:
- Efficient document chunking and storage
- Source-based document tracking
- Easy document retrieval and deletion
- Seamless integration with the RAG system

## Running the Application-the Correct way to run the application

`python -m langchain_rag_pilot.main`

# Common errors and their solutions:
1. Incorrect: python -m langchain_rag_pilot/main.py
- Error: ModuleNotFoundError: No module named 'langchain_rag_pilot/main'
- Solution: Remove the .py extension when using -m flag

2. Incorrect: python -u "langchain_rag_pilot/main"
- Error: ImportError: attempted relative import with no known parent package
- Solution: Use the module syntax with -m flag to ensure proper package imports

3. If you see "No module named langchain_rag_pilot":
- Solution: Ensure the package is installed in development mode:
- pip install -e .

# Note about deprecation warnings:
 - If you see a warning about ConversationBufferMemory, it's normal
 - The system now uses ChatMessageHistory from langchain_core for better memory management
 - This warning doesn't affect functionality but indicates we're using the newer approach

## Personal Environment Dependency conflict
- Note about the dependency conflict:
You'll see this warning:
``` 
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
langflow 1.5.0.post1 requires youtube-transcript-api==0.6.3, but you have youtube-transcript-api 1.2.3 which is incompatible.
```
- This is because you have langflow installed globally in your pyenv Python (not in this venv). It won't affect your project since the venv is isolated. 
- If you want to fix it, you can either:
* Ignore it (recommended - it's in your global environment, not this project)
* Or uninstall langflow from your global pyenv: `pip uninstall langflow`
* Your Mac: You are on an Intel-based Mac (x86_64). 
* The Package: PyTorch (the torch package) stopped releasing pre-built wheels for Intel Macs after version 2.2.x. 
* The Error: Your project is trying to install torch==2.9.1, which only has wheels for Apple Silicon (arm64) Macs, not your Intel Mac.

## Docker Support
TBD

### Building the Container

## Resetting the Database and Vector Store

To clear all indexed documents and sources and start over:

# Remove all Chroma vector store data
`rm -rf chroma_db/* `

# Remove all tracked sources from the database (but keep the DB file)

`sqlite3 sources.db 'DELETE FROM sources;' `

## (Optional) To completely remove the sources database file:
` rm sources.db `


## Interacting with the Sources Database (`sources.db`)
All commands below assume you are in the project root directory:

`/Users/curtisoneal/Documents/DataScience/github_2025_home/Meetup_Langchain`

### List all tracked sources
`sqlite3 sources.db 'SELECT * FROM sources;' `
 `sqlite3 sources.db 'SELECT COUNT(*) FROM sources;'
  -59

### Clear all tracked sources (but keep the database file)
`sqlite3 sources.db 'DELETE FROM sources;' `

### Remove the sources database file entirely (start completely fresh)
` rm sources.db `

**Note:**
- You must be in the project root directory (where `sources.db` is located) to run these commands.
- If you remove `sources.db`, it will be recreated automatically the next time you run the application, but all previous source tracking will be lost.

## Pytest Notes
`pytest -q`
pytest --> runs all tests and shows full details
-q --> quiet mode, reducing noise

What "quiet mode" changes:
Hides the verbose test discovery
Hides fixture setup/teardown chatter
Hides extra headers and plugin information
Only prints:
a dot for each passing test
F or E for failures/errors
a short summary at the end

### Options:
pytest -v --> verbose mode (shows each test name)
pytest -vv --> very verbose (shows parametrized test expansions)
pytest -x --> stop after first failure
pytest --maxfail=1 --> similar to -x but configurable
pytest -q --disable-warnings --> quiet + hide warnings
pytest -q --tb=short --> quiet + short tracebacks
