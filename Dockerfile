# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files AND README (required for hatchling build)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies into a virtual environment
# We use --no-dev to exclude test dependencies
# We use --frozen to ensure we use the exact versions from uv.lock
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Install system dependencies (ffmpeg is required for audio processing)
# Install deno for yt-dlp's JS runtime requirement
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    unzip \
    && curl -fsSL https://deno.land/x/install/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY src ./src
COPY summarize_prompt.txt ./

# Set environment variables
# Add deno to the PATH
ENV PATH="/root/.deno/bin:/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
# Ensure output is unbuffered (logs show up immediately)
ENV PYTHONUNBUFFERED=1

# Define the entrypoint
ENTRYPOINT ["python", "-m", "video2mdnotes.main"]

# Default command (can be overridden)
CMD ["--help"]
