#!/usr/bin/env bash

set -u  # be strict about undefined variables, but don't use -e/pipefail yet

PROMPT_FILE="summarize_prompt.txt"
MODEL="gpt-4o-mini"
OUT_DIR="summaries"
TRANS_DIR="transcribed_wav"
ARCHIVE_DIR="$TRANS_DIR/archive"

# Check prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
  echo "ERROR: $PROMPT_FILE not found in $(pwd)" >&2
  exit 1
fi

# Load prompt into a variable once
PROMPT="$(cat "$PROMPT_FILE")"

# Ensure output directory exists
mkdir -p "$OUT_DIR"
# Ensure directory for moved/processed wav files exists
mkdir -p "$TRANS_DIR"
# Ensure archive directory exists for processed wavs
mkdir -p "$ARCHIVE_DIR"

# Loop over all transcript Markdown files
for md in transcripts/*.md; do
  # If the glob doesn't match anything, skip
  [ -f "$md" ] || continue

  base="$(basename "$md" .md)"
  out="$OUT_DIR/${base}.summary.md"

  if [ -s "$out" ]; then
    echo "Skipping $md (non-empty summary already exists at $out)"
    continue
  fi

  echo "Summarizing $md -> $out"

  # Feed the transcript as STDIN, write summary to $out
  if ! llm -m "$MODEL" -s "$PROMPT" < "$md" > "$out"; then
    echo "ERROR: llm failed on $md, removing $out" >&2
    rm -f "$out"
  else
    # After successfully creating a summary, archive the corresponding .wav
    # Prefer wavs in $TRANS_DIR (produced by transcribe_dir.py), fall back to
    # project root if present.
    base_wav_name="${base}.wav"
    src1="$TRANS_DIR/$base_wav_name"
    src2="$base_wav_name"
    if [ -f "$src1" ]; then
      echo "Archiving processed wav $src1 -> $ARCHIVE_DIR/"
      mv "$src1" "$ARCHIVE_DIR/"
    elif [ -f "$src2" ]; then
      echo "Archiving processed wav $src2 -> $ARCHIVE_DIR/"
      mv "$src2" "$ARCHIVE_DIR/"
    fi
  fi
done

