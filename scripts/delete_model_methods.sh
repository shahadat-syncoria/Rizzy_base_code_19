#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SOURCE_ROOT="${1:-$SCRIPT_DIR/Odoo_sync_compiled_script}"
TARGET_ROOT="${2:-$SCRIPT_DIR/Odoo_sync_ready_for_run_script}"

if [[ ! -d "$SOURCE_ROOT" ]]; then
    echo "Source add-ons root not found: $SOURCE_ROOT" >&2
    exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
    echo "Required command not found: rsync" >&2
    exit 1
fi

rm -rf "$TARGET_ROOT"
mkdir -p "$TARGET_ROOT"

echo "Copying source tree:"
echo "  from: $SOURCE_ROOT"
echo "  to:   $TARGET_ROOT"
rsync -a \
    --delete \
    "$SOURCE_ROOT"/ "$TARGET_ROOT"/

FOUND_MODELS_DIR=0
FOUND_ELIGIBLE_MODELS_DIR=0

while IFS= read -r -d '' models_dir; do
    FOUND_MODELS_DIR=1

    if [[ ! -d "$models_dir/table_models" ]]; then
        echo
        echo "Skipping: $models_dir (no table_models directory)"
        continue
    fi

    FOUND_ELIGIBLE_MODELS_DIR=1
    echo
    echo "Cleaning: $models_dir"
    while IFS= read -r -d '' py_file; do
        echo "Removing: $py_file"
        rm -f "$py_file"
    done < <(
        find "$models_dir" -mindepth 1 -maxdepth 1 -type f -name '*.py' ! -name '__init__.py' -print0 | sort -z
    )
done < <(find "$TARGET_ROOT" -type d -name models -print0 | sort -z)

if [[ "$FOUND_MODELS_DIR" -eq 0 ]]; then
    echo "No models directories found under: $TARGET_ROOT" >&2
    exit 1
fi

if [[ "$FOUND_ELIGIBLE_MODELS_DIR" -eq 0 ]]; then
    echo "No models directories with table_models found under: $TARGET_ROOT"
fi
