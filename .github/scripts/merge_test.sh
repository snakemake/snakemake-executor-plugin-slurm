#!/usr/bin/env bash

set -euo pipefail

# CONFIGURATION
UPSTREAM_REMOTE="upstream"
UPSTREAM_BRANCH="main"
FORK_BRANCH="main"
TEMP_DIR=".merge-tmp"

EXCLUDES=(
    "TODO.md"
    "tests/Snakefile"
    "tests/tests.py"
    "tests/__pycache__"
    "tests/profiles"
)
# Check if the script is run from the correct directory
echo "Preparing for local 3-way sync test (upstream → cannon)..."

# Ensure remotes are up to date
git fetch $UPSTREAM_REMOTE
git fetch origin

# Find the common ancestor (merge base)
BASE_COMMIT=$(git merge-base origin/$FORK_BRANCH $UPSTREAM_REMOTE/$UPSTREAM_BRANCH)
echo "Using merge base: $BASE_COMMIT"

# Prepare temp workspace
mkdir -p $TEMP_DIR/base $TEMP_DIR/theirs $TEMP_DIR/mine $TEMP_DIR/preview

MERGED=false

# Gather tracked files from upstream
FILES=$(git ls-tree -r --name-only $UPSTREAM_REMOTE/$UPSTREAM_BRANCH)

for SRC in $FILES; do
    # (skip exclusions and map paths as before)

    # Map slurm ➞ cannon
    if [[ "$SRC" == snakemake_executor_plugin_slurm/* ]]; then
        DEST="${SRC/snakemake_executor_plugin_slurm/snakemake_executor_plugin_cannon}"
    else
        DEST="$SRC"
    fi

    [[ ! -f "$DEST" ]] && continue

    echo "Merging $SRC -> $DEST"

    TMP_BASE="$TEMP_DIR/base/$(basename "$DEST")"
    TMP_THEIRS="$TEMP_DIR/theirs/$(basename "$DEST")"
    TMP_MINE="$TEMP_DIR/mine/$(basename "$DEST")"

    git show "$BASE_COMMIT:$SRC" > "$TMP_BASE" 2>/dev/null || continue
    git show "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH:$SRC" > "$TMP_THEIRS" || continue
    cp "$DEST" "$TMP_MINE"

    if git merge-file --marker-size=30 "$TMP_MINE" "$TMP_BASE" "$TMP_THEIRS"; then
        echo "Clean merge completed: $DEST"
    else
        echo "Conflict detected: $DEST (manual resolution may be required)"
    fi

    echo "Diff between $DEST and merged result:"
    diff -u "$DEST" "$TMP_MINE" || true
    echo

    read -p "Apply merged result to $DEST? [y/N]: " CONFIRM
    if [[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]]; then
        cp "$TMP_MINE" "$DEST"
        echo "Applied merged version to $DEST"
        MERGED=true
    else
        echo "Skipped applying merged version to $DEST"
    fi

    rm -f "$TMP_BASE" "$TMP_THEIRS" "$TMP_MINE"
done

echo ""
echo "Merge simulation complete."
echo "Merged files are available under: $TEMP_DIR/preview/"
echo "No files in your working directory were modified."
echo "To apply changes, manually copy from preview/ into your repo and commit."