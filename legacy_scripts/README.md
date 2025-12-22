# Legacy Scripts Archive

This directory contains the original Bash and Python scripts used in the early versions of `video2mdnotes`.

**These scripts are now obsolete.** They have been superseded by the modern, containerized Python application in the `src/` directory.

## Contents

*   **`clean_dir_filenames.sh`**: A bash script to sanitize filenames (replace spaces, lowercase, etc.).
*   **`transcribe_dir.py`**: A standalone Python script using `faster-whisper` to transcribe all `.wav` files in the current directory.
*   **`batch_run.sh`**: A bash script that iterated over transcripts and called the `llm` CLI tool to generate summaries.
*   **`structure_previous_run.sh`**: A helper script for organizing output.
*   **`summaries/`, `transcripts/`, `transcribed_wav/`**: Legacy output directories.

## How to Use (If absolutely necessary)

These scripts were designed to run from the **project root**. If you need to run them:

1.  Copy the script you need back to the project root:
    ```bash
    cp legacy_scripts/transcribe_dir.py .
    ```
2.  Ensure you have the necessary local dependencies installed (see `human_readable_documentation/Original_Script_based_User_Guide.md`).
3.  Run the script from the root.

**Note:** Do not run these scripts directly from inside the `legacy_scripts/` directory, as they rely on relative paths that will be incorrect.
