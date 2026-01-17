# Fast Video Notetaker v2

The point of this project is to have a robust Python application that, when provided the URL of a video or video playlist, will download the audio, create a transcript, and use an LLM to generate a structured summary.

This project has been refactored from a collection of scripts into a modern, containerized Python application.

## Project Structure
The project now follows a standard Python package structure:
```
video2mdnotes/
├── .clinerules/         # Internal documentation and project plans
├── .dockerignore        # Files to ignore for Docker builds
├── .env.example         # Template for environment variables
├── .gitignore           # Files ignored by Git
├── docker-compose.yml   # Defines the application service for Docker
├── Dockerfile           # Instructions to build the application container
├── human_readable_documentation/ # User guides and project documentation
├── legacy_scripts/      # The original, now-obsolete scripts
├── previous_run_results/ # Default output directory for processed videos
├── pyproject.toml       # Project definition, dependencies, and tools
├── src/                 # Main application source code
│   └── video2mdnotes/
├── summarize_prompt.txt # The prompt used for the LLM summarizer
└── tests/               # Automated tests for the application
```

### Package Management
This project uses modern Python packaging tools:
- **uv**: A fast, reliable package installer and virtual environment manager.
- **hatchling**: The build backend used for packaging the application.
- **pyproject.toml**: The single configuration file for defining the project and its dependencies.

## Project Setup

### Prerequisites
- **Docker**: Docker Desktop (for Mac/Windows) or Docker Engine (for Linux) must be installed and running.
- **API Key**: You need an API key from an LLM provider (like OpenAI or Anthropic) to generate summaries.

### Quick Start
1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd video2mdnotes
    ```

2.  **Create Environment File:**
    Copy the `.env.example` file to `.env` and add your API key.
    ```bash
    cp .env.example .env
    # Now, edit .env and add your key:
    # OPENAI_API_KEY="sk-..."
    ```

3.  **Build the Docker Container:**
    This command builds the application image. You only need to run this once, or whenever you change the Python code.
    ```bash
    docker compose build
    ```

## How to Run

You can run the application in three ways: as a CLI tool, as an API server, or interactively.

### 1. CLI Mode (One-off Process)
This is the simplest way to process a single video or playlist.
```bash
docker compose run --rm app "YOUR_VIDEO_OR_PLAYLIST_URL"
```
*   **`--rm`**: Automatically removes the container after the job finishes.
*   **Options**: You can pass flags like `--no-keep-wav` after the URL.

### 2. API Mode (Continuous Server)
Run the application as a REST API with a Swagger UI.
```bash
docker compose up api
```
*   **Access**: Open your browser to **http://127.0.0.1:8000/docs**.
*   **Usage**: Use the `POST /process` endpoint to submit URLs.
*   **Shutdown**: Press `Ctrl+C` in the terminal to gracefully stop the server.

### 3. Interactive Mode (Shell)
Start a shell inside the container to run commands manually.
```bash
docker compose run --rm app /bin/bash
```
*   **Inside the container**: You can run `python -m video2mdnotes.main "URL"` repeatedly.
*   **Exit**: Type `exit` to leave the container.

### Expected Output
After a successful run, a new directory will be created in `previous_run_results/` containing the final summary, the raw transcript, the original URL, and (optionally) the downloaded audio file.

## Development
If you want to modify the code or run tests locally, you'll need a local Python environment.

### Local Setup
1.  **Install Python**: We recommend Python 3.11.
2.  **Install uv**:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
3.  **Create Virtual Environment & Install Dependencies**:
    This command reads the `pyproject.toml` and installs all production and development dependencies.
    ```bash
    uv sync --with-dev
    ```
4.  **Activate Virtual Environment**:
    ```bash
    source .venv/bin/activate
    ```

### Development Tools
Once your local environment is set up, you can use these commands.

**Run Tests:**
```bash
uv run pytest
```

**Run Linter & Formatter:**
This project uses `ruff` to check for errors and format the code.
```bash
# Check for errors
uv run ruff check .

# Automatically fix fixable errors
uv run ruff check . --fix

# Format all files
uv run ruff format .
```
