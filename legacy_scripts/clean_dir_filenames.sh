#!/usr/bin/env bash
#
# clean_dir_filenames.sh - Normalize filenames by removing problematic characters and applying consistent formatting.
#
# Usage:
#   ./clean_dir_filenames.sh [--dry-run] [target_directory]
#
# Transformations applied (in order):
#   1. Replace dashes with underscores
#   2. Replace whitespace with underscores
#   3. Prefix ISO date (YYYYMMDD_) to the filename
#   4. Convert to lowercase
#   5. Remove special characters (replaced with underscores)
#
# Example:
#   ./clean_dir_filenames.sh                    # Process current directory
#   ./clean_dir_filenames.sh --dry-run          # Show what would be renamed without changing files
#   ./clean_dir_filenames.sh /path/to/dir       # Process specified directory
#   ./clean_dir_filenames.sh --dry-run /path/to/dir
#

set -u

DRY_RUN=false
TARGET_DIR="."

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -*)
      echo "ERROR: Unknown option: $1" >&2
      exit 1
      ;;
    *)
      TARGET_DIR="$1"
      shift
      ;;
  esac
done

# Verify directory exists
if [ ! -d "$TARGET_DIR" ]; then
  echo "ERROR: Directory not found: $TARGET_DIR" >&2
  exit 1
fi

echo "Target directory: $TARGET_DIR"
echo "Dry run: $DRY_RUN"
echo ""

count=0

# Process all files in target directory (non-recursively)
for filepath in "$TARGET_DIR"/*; do
  [ -e "$filepath" ] || continue
  
  # Only process regular files
  if [ ! -f "$filepath" ]; then
    continue
  fi
  
  # Extract directory and filename
  dir="$(dirname "$filepath")"
  oldname="$(basename "$filepath")"
  
  # Skip if already processed or hidden files
  [ "${oldname:0:1}" = "." ] && continue

  # Skip files we do not want to modify: scripts, text files, python files, and README
  case "$oldname" in
    *.sh|*.txt|*.py)
      continue
      ;;
    README.md|readme.md)
      continue
      ;;
  esac
  
  # Build the new filename step by step
  newname="$oldname"
  
  # 1. Replace dashes with underscores
  newname="${newname//-/_}"
  
  # 2. Replace whitespace (spaces, tabs, newlines) with underscores
  newname="$(echo "$newname" | sed -E "s/[[:space:]]+/_/g")"
  
  # 3. Prefix ISO date (YYYYMMDD_) to the filename
  # Separate extension and basename
  if [[ "$newname" == *.* ]]; then
    extension="${newname##*.}"
    basename="${newname%.*}"
    newname="$(date +%Y%m%d)_${basename}.${extension}"
  else
    newname="$(date +%Y%m%d)_${newname}"
  fi
  
  # 4. Convert to lowercase
  newname="$(echo "$newname" | tr "[:upper:]" "[:lower:]")"
  
  # 5. Remove/replace special characters
  # Keep: alphanumerics, underscores, dots (in extensions), dashes (now underscores)
  # Replace most special chars with underscores
  if [[ "$newname" == *.* ]]; then
    extension="${newname##*.}"
    basename="${newname%.*}"
    # Remove special chars from basename, then add extension back
    basename="$(echo "$basename" | tr -cd "a-z0-9_-." | tr -d "!@#$%^&*()+=,;:<>?/[]{}|\\\"'")"
    newname="${basename}.${extension}"
  else
    newname="$(echo "$newname" | tr -cd "a-z0-9_-." | tr -d "!@#$%^&*()+=,;:<>?/[]{}|\\\"'")"
  fi
  
  # Skip if name didn't change
  if [ "$oldname" = "$newname" ]; then
    continue
  fi
  
  count=$((count + 1))
  
  newpath="$dir/$newname"
  
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] $oldname -> $newname"
  else
    if [ -e "$newpath" ]; then
      echo "WARNING: Target file already exists, skipping: $oldname -> $newname"
    else
      mv "$filepath" "$newpath"
      echo "Renamed: $oldname -> $newname"
    fi
  fi
done

echo ""
echo "Total files processed: $count"
