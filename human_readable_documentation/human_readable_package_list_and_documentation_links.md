# Project Dependencies

This document provides a comprehensive list of all packages and major dependencies used in the `video2mdnotes` project.

## Python Packages

These packages are managed by `uv` and defined in `pyproject.toml`.

| Package Name | Purpose | Documentation URL |
|---|---|---|
| `fastapi` | High-performance web framework for building APIs. | [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/) |
| `faster-whisper` | Optimized implementation of OpenAI's Whisper model for transcription. | [https://github.com/guillaumekln/faster-whisper](https://github.com/guillaumekln/faster-whisper) |
| `litellm` | Lightweight library to call 100+ LLM APIs with a consistent format. | [https://docs.litellm.ai/](https://docs.litellm.ai/) |
| `loguru` | Simple and powerful logging library for application monitoring. | [https://loguru.readthedocs.io/en/stable/](https://loguru.readthedocs.io/en/stable/) |
| `pydantic-settings` | Manages application settings from `.env` files and environment variables. | [https://docs.pydantic.dev/latest/concepts/pydantic_settings/](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| `rich` | Library for rich text and beautiful formatting in the terminal. | [https://rich.readthedocs.io/](https://rich.readthedocs.io/) |
| `typer` | Library for building modern Command Line Interfaces (CLIs). | [https://typer.tiangolo.com/](https://typer.tiangolo.com/) |
| `uvicorn` | High-performance ASGI server for running FastAPI applications. | [https://www.uvicorn.org/](https://www.uvicorn.org/) |
| `yt-dlp` | A feature-rich program to download video/audio from YouTube and other sites. | [https://github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| `pytest` (dev) | A framework for writing and running tests. | [https://docs.pytest.org/](https://docs.pytest.org/) |
| `ruff` (dev) | An extremely fast Python linter and code formatter. | [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/) |
| `mypy` (dev) | A static type checker for Python. | [https://mypy-lang.org/](https://mypy-lang.org/) |

## System-Level Dependencies

These dependencies are required by the runtime environment, as defined in the `Dockerfile`.

| Dependency | Purpose | Documentation/Info URL |
|---|---|---|
| `Docker` | Platform for developing, shipping, and running applications in containers. | [https://docs.docker.com/](https://docs.docker.com/) |
| `ffmpeg` | A solution to record, convert, and stream audio and video. Required by `yt-dlp` and `faster-whisper`. | [https://ffmpeg.org/documentation.html](https://ffmpeg.org/documentation.html) |
| `deno` | A modern runtime for JavaScript, used by `yt-dlp` to handle complex video sources. | [https://deno.land/manual](https://deno.land/manual) |
