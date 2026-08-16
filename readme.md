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
- **A summarization backend**: either a logged-in `claude` CLI (subscription, no
  API key), an LLM provider API key, or a local model server. See
  [Choosing a summarization backend](#choosing-a-summarization-backend) — this is
  a real setup decision, not a default to skip past.

### Choosing a summarization backend

The model chosen here does **not** affect transcription accuracy at all — but it
substantially changes how good the notes are, and it is easy to end up with a
weaker model doing the work without noticing.

#### The pipeline has two separate model steps

| Step | What runs it | Your choice? |
|---|---|---|
| **Transcription** (audio → text) | `faster-whisper`, locally on CPU | Model size only (`FW_MODEL`, default `medium`). No API, no key, no network. |
| **Summarization** (text → notes) | An LLM, via one of the backends below | **Yes — this section.** |

Nothing in this section touches transcription. A "cheaper model" here means
thinner *notes*, never a worse *transcript*.

#### The chain

`LLM_MODELS` is an ordered **failover** chain, not a quality ladder. Entry 1 does
essentially all the work; later entries fire only when an earlier one *errors*.
**Putting a cheap model first makes it your summarizer.** The default:

```
LLM_MODELS=["claude-cli/opus", "claude-cli/sonnet", "openai/gpt-4o"]
```

**1. Subscription CLI (`claude-cli/…`) — no metered cost**

Shells out to the `claude` CLI, which authenticates with your logged-in Claude
subscription (macOS keychain) rather than an API key. Requires the CLI installed
and logged in. Bounded by your subscription's rate limits, which is exactly why a
metered entry sits behind it in the default chain. Aliases: `opus`, `sonnet`,
`haiku`.

**2. Metered API (`openai/…`, `anthropic/…`) — billed per token**

Standard REST via litellm using `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`. No rate
ceiling, but every run costs money and a full transcript is a large prompt. These
keys are often shared with other tools on the same machine, so the usage lands on
the same bill.

**3. Local models (`ollama/…`, `lm_studio/…`) — privacy option, off by default**

```
ALLOW_LOCAL_MODELS=true
LLM_MODELS=["ollama/llama3.1", "claude-cli/opus"]
```

Requires Ollama or LM Studio installed and serving. **Use this when the content
must not leave the machine** — private recordings, client material, anything
under NDA. Both the transcription and summarization steps then run entirely
locally, so a full run touches the network only to fetch the source video.

It is gated behind `ALLOW_LOCAL_MODELS` deliberately: local models need no API
key, so without the gate a misconfigured chain could silently fall through to a
much weaker model and emit notes that *look* fine. Expect noticeably shallower
analysis than the hosted models — `summarize_prompt.txt` was tuned and validated
against frontier models, and that validation does not carry over.

#### Measured model comparison

Same transcript, same prompt, tools disabled, summarization step only:

| Model | Time | Output | What you get |
|---|---|---|---|
| `haiku` | 16s | 3.3 KB | Accurate and faithful. Restates what was said, correct section discipline, little added analysis. |
| `sonnet` | 35s | 5.5 KB | Balanced. Adds domain framing and some nuance. |
| `opus` | 54s | 9.1 KB | Different in kind, not just longer — cites timestamp ranges, derives operational consequences the transcript never states, and explicitly names what is *absent* from the source. |

All three produced the same 8 sections and the same 3 correct `- None` answers,
so structural compliance is not the differentiator — analytical depth is. Use
`haiku` for bulk or playlist runs where coverage beats insight; `opus` for
material you actually intend to study.

#### Why tools are disabled on the CLI backend

`claude -p` is an **agent**, not a plain completion endpoint — by default it can
load skills, search the web, and read files. Left enabled, this backend:

- **Breaks grounding.** Observed live: summarizing a transcript about Claude
  models, the agent loaded API documentation and wrote confident,
  documentation-sourced claims into "Fact-Checked Notes" — a section the prompt
  deliberately instructs the model to *hedge* precisely because it is supposed to
  have no external lookup (see [Summarization behavior](#summarization-behavior)).
  Verified and unverified claims become indistinguishable.
- **Makes runs non-reproducible**, since output depends on what the agent chose
  to look up that time.
- **Opens a prompt-injection surface.** Transcripts are untrusted third-party
  content. An agent with file and shell access, summarizing text an attacker
  controls, is a bad combination.

So the CLI backend always passes `--disallowedTools` and runs from a scratch
working directory (a repo cwd would pull that repo's `CLAUDE.md` into an
unrelated summarization job). Both are configurable but neither should be
removed.

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

### Transcript sourcing (captions-first)

Before downloading any audio, the pipeline probes the source for an existing
**human-authored** caption track. If it finds a usable one, it uses that and
skips both the audio download and the Whisper run — on a ~19-minute video that
is roughly ten minutes of work avoided. Otherwise it downloads audio and
transcribes locally, exactly as before.

Every transcript records where it came from, in its own front matter:

```yaml
transcript_source: captions (manual, en)   # or: whisper
```

ASR output and a human-authored transcript are not interchangeable evidence, so
this is recorded rather than left to be inferred from the model field.

**Machine captions are never used.** yt-dlp separates human-authored `subtitles`
from machine `automatic_captions`, and only the former are accepted. Auto-captions
are ASR *without* the vocabulary hint `build_initial_prompt()` supplies, so using
them would reintroduce the exact error class that hint exists to fix
("Claude" → "Cloud"). They are also silently machine-translated — a probe of one
English video listed `ab` (Abkhazian) among its automatic captions. Local Whisper
is the better fallback.

**A caption track must prove it carries speech.** Music videos return tracks that
are entirely `[♪♪♪]` / `[Music]` cues; those pass a naive "are there segments?"
check and would feed the summarizer garbage it is then obliged to summarize. A
track yielding fewer than `CAPTIONS_MIN_WORDS` word-equivalents is rejected in
favour of Whisper. Erring this way only ever costs time, never correctness.

**Language selection.** `CAPTIONS_LANG` is an ordered, comma-separated
preference — `en,ja` tries English then Japanese. The token `any` accepts
whatever manual track the source ships, which is how content in an unanticipated
language stays reachable on an otherwise English install:

```
CAPTIONS_LANG=en,any
```

Each entry matches on language prefix, so `en` accepts `en-US`/`en-GB`, with an
exact match preferred. Empty falls back to `FW_LANG`. It is kept separate from
`FW_LANG` because that setting tells Whisper what to expect, whereas a source in
another language can still be worth taking captions from.

Japanese, Chinese and Korean are **not** space-delimited, so the speech guard
counts CJK characters directly (roughly two characters per word-equivalent)
rather than counting spaced words — otherwise every CJK track would score zero
and be rejected as "no speech."

Disable the whole behavior with `CAPTIONS_FIRST=false` to always transcribe
locally.

### Long runs: resuming and running out of capacity

A playlist of long videos is many large prompts, so a research run can exhaust
your subscription partway through. Two behaviors exist for that.

**Finished work is never redone.** Any video that already has a summary on disk
is skipped, matched on title independent of run date. Re-running the same
command continues where it stopped:

```
[1/10] Skipping (already summarized): But what is a neural network?...
[5/10] Processing: Large Language Models explained briefly
```

Pass `--force` to re-summarize everything anyway — e.g. to redo a playlist with
a better model.

**Running out of capacity does not silently start costing money.** When the
subscription backend is exhausted, the chain does **not** fall through to a paid
backend by default. `--on-exhaustion` controls what happens instead:

| Mode | Behavior |
|---|---|
| `wait` *(default)* | Alert, sleep until the limit resets, retry the same video. Uses a reset time from the CLI when it reports one, else `EXHAUSTION_WAIT_SECONDS`. |
| `metered` | Continue on the paid backends in `LLM_MODELS`. |
| `local` | Continue on local backends only (needs `ALLOW_LOCAL_MODELS`). Never reaches a paid backend. |
| `stop` | Stop cleanly. Finished videos are kept and skipped on resume. |
| `ask` | Prompt once, then apply that answer for the rest of the run. |

`wait` is the default deliberately. An unattended run — a research agent that
cannot answer a prompt — must not begin spending money merely because nobody was
there to say no; it waits for capacity already paid for. `ask` degrades to
`wait`, not to spending, when there is no TTY.

Exhaustion is also distinguished from ordinary failure: a crashed backend still
fails over normally, and one bad video no longer abandons the rest of a
playlist. Every run ends with a ledger of summarized / skipped / failed, and
names the video it stopped on.

### Summarization behavior
`summarize_prompt.txt` is domain-adaptive: it detects whether the source content is
technical (programming/ML/data/architecture) or Aikido/martial arts, and interprets each
output section accordingly (e.g. "New Commands / Techniques" means CLI commands for
technical content, named techniques/drills for Aikido). It also includes a "Sponsor / Ad
Content" section that separates podcast sponsor reads from editorial content instead of
mixing them in or dropping them, grounding instructions against fabricating content for
thin/empty transcripts, and confidence-calibrated fact-checking (the summarizer has no web
search, so it's asked to flag its own uncertainty rather than assert flatly). Ported from
base_human_learn_sys and validated 2026-08-08 against real technical (AI Daily Brief
podcast) and Aikido content.

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
