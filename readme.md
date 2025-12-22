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

## User Guide
See /human_readable_documentation/Current_User_Guide.md for a short user friendly version of the commands and usage.

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
The application is run as a command inside the Docker container.

### Process a Single Video or Playlist
This is the main command. It will download, transcribe, summarize, and archive the content from the URL.
```bash
docker compose run --rm app "YOUR_VIDEO_OR_PLAYLIST_URL"
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
Note:  `uv run pytest` runs all tests, including the end-to-end (E2E) tests.
Since the E2E tests involve downloading, transcribing, and summarizing real videos (even short ones), they take significantly longer than the unit tests. The playlist test, in particular, processes two videos, so it will take a few minutes.

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

# Alternate instructions for Container use with Commandline terminal
A different workflow, and that requires a slight change in how we think about the container. Instead of running a one-off script, you can use an interactive session inside the container.

## Here's how you do it:
1. Start an Interactive Shell
You'll tell Docker to start the container and run a shell (/bin/bash) instead of your Python script. The -it flags are crucial:
• -i (interactive): Keeps STDIN open.
• -t (tty): Allocates a pseudo-TTY, which gives you a proper terminal interface.
Command to run:
Shell Script
`docker compose run --rm app /bin/bash`
(Note: We still use --rm so the container is deleted when you exit the shell, keeping things clean).

2. What Happens Next
After running that command, your terminal prompt will change. It will look something like this:
`root@<container_id>:/app#`
You are now inside the container. From here, you can run your Python script as many times as you want, just like you would on your local machine, but using the container's environment.

3. Running Commands Inside the Container
Once you have the shell prompt, you can run your script directly:
```Shell Script
# Run with a URL
python -m video2mdnotes.main "https://www.youtube.com/watch?v=tPEE9ZwTmy0"

# Run with another URL
python -m video2mdnotes.main "https://www.youtube.com/watch?v=another-video"

# Shell Script
 Explore the container's filesystem
ls -l /app
```

4. Exiting the Container
When you are finished, simply type exit and press Enter.
```Shell Script
root@<container_id>:/app# exit
```

This will terminate the shell, and because you used the --rm flag, Docker will automatically delete the container.
