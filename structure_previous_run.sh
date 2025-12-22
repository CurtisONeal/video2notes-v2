#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME=$(basename "$0")

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [--name SHORT] [--dirs DIR1,DIR2] [--dry-run]

Create a timestamped run folder under previous_run_results/ and move
current in-process directories into it. Creates a per-run .gitignore that
ignores all results and a .gitkeep to keep the folder tracked.

Options:
  -n, --name SHORT      Short name to append to timestamp (no spaces)
  -d, --dirs LIST       Comma-separated list of directories to move
                        (default: transcripts,summaries,transcribed_wav,results)
      --dry-run         Show what would be moved without performing actions
  -h, --help            Show this help
EOF
}

DRY_RUN=false
SHORT_NAME=""
DIRS="transcripts,summaries,transcribed_wav,results"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--name)
      SHORT_NAME="$2"
      shift 2
      ;;
    -d|--dirs)
      DIRS="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

TS=$(date -u +"%Y%m%d_%H%M%SZ")
RUN_NAME="$TS"
if [[ -n "$SHORT_NAME" ]]; then
  # sanitize short name: keep alphanum, dash, underscore
  SAFE=$(echo "$SHORT_NAME" | tr -c '[:alnum:]_-' '_')
  RUN_NAME="${RUN_NAME}_$SAFE"
fi

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PREV_DIR="$ROOT_DIR/previous_run_results"
RUN_DIR="$PREV_DIR/$RUN_NAME"

IFS=',' read -r -a DIR_ARR <<< "$DIRS"

echo "Run folder: $RUN_DIR"
echo "Dirs to consider: ${DIR_ARR[*]}"
if $DRY_RUN; then
  echo "(dry-run)"
fi

mkdir -p "$PREV_DIR"

# Ensure the previous_run_results folder has a .gitkeep so it's tracked
if [[ ! -f "$PREV_DIR/.gitkeep" ]]; then
  if $DRY_RUN; then
    echo "(dry-run) would create: $PREV_DIR/.gitkeep"
  else
    echo "# keep this directory in git" > "$PREV_DIR/.gitkeep"
  fi
fi

# Evaluate moves
MOVED=0
for d in "${DIR_ARR[@]}"; do
  SRC="$ROOT_DIR/$d"
  if [[ ! -e "$SRC" ]]; then
    echo "Skipping missing: $d"
    continue
  fi
  # don't move previous_run_results or the run dir itself
  if [[ "$SRC" == "$PREV_DIR" || "$SRC" == "$RUN_DIR" || "$SRC" == "$ROOT_DIR/previous_run_results" ]]; then
    echo "Skipping disallowed path: $SRC"
    continue
  fi
  # If it's an empty dir, skip
  if [[ -d "$SRC" && -z "$(ls -A "$SRC")" ]]; then
    echo "Skipping empty directory: $d"
    continue
  fi

  if $DRY_RUN; then
    echo "(dry-run) Would move: $SRC -> $RUN_DIR/"
  else
    mkdir -p "$RUN_DIR"
    echo "Moving: $SRC -> $RUN_DIR/"
    mv "$SRC" "$RUN_DIR/"
    MOVED=$((MOVED+1))
  fi
done

if $DRY_RUN; then
  echo "Dry-run complete. To perform the moves, run: $SCRIPT_NAME --name $SHORT_NAME"
  exit 0
fi

# After moving, create run-level .gitignore and .gitkeep
if [[ ! -d "$RUN_DIR" ]]; then
  echo "No items moved; not creating run folder. Exiting."
  exit 0
fi

echo "Creating run-level placeholders in $RUN_DIR"
cat > "$RUN_DIR/.gitignore" <<'GITIGNORE'
*
!.gitkeep
GITIGNORE

echo "# keep this run folder in git" > "$RUN_DIR/.gitkeep"

echo "Done. Moved $MOVED items into $RUN_DIR"
echo "Remember: per-run results are ignored from git by the run-level .gitignore"

exit 0
