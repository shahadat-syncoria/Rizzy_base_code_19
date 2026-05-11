#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SOURCE_ROOT="${1:-$SCRIPT_DIR/Odoo_sync_compile_left_script}"
TARGET_ROOT="${2:-$SCRIPT_DIR/Odoo_sync_compiled_script}"
PYTHONS=("python3.10" "python3.11" "python3.12")

if [[ ! -d "$SOURCE_ROOT" ]]; then
    echo "Source add-ons root not found: $SOURCE_ROOT" >&2
    exit 1
fi

declare -a MODEL_DIRS=()
declare -a AVAILABLE_PYTHONS=()
FAILED=0

rm -rf "$TARGET_ROOT"
mkdir -p "$TARGET_ROOT"

if ! command -v rsync >/dev/null 2>&1; then
    echo "Required command not found: rsync" >&2
    exit 1
fi

echo "Copying source tree:"
echo "  from: $SOURCE_ROOT"
echo "  to:   $TARGET_ROOT"
rsync -a \
    --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    "$SOURCE_ROOT"/ "$TARGET_ROOT"/

while IFS= read -r -d '' models_dir; do
    MODEL_DIRS+=("$models_dir")
done < <(find "$TARGET_ROOT" -type d -name models ! -path '*/static/*' -print0 | sort -z)

if [[ ${#MODEL_DIRS[@]} -eq 0 ]]; then
    echo "No Python models directories found under: $TARGET_ROOT" >&2
    exit 1
fi

for py in "${PYTHONS[@]}"; do
    if command -v "$py" >/dev/null 2>&1; then
        AVAILABLE_PYTHONS+=("$py")
    else
        echo "Skipping missing interpreter: $py"
    fi
done

if [[ ${#AVAILABLE_PYTHONS[@]} -eq 0 ]]; then
    echo "No requested Python interpreters are installed." >&2
    exit 1
fi

for models_dir in "${MODEL_DIRS[@]}"; do
    relative_models_dir="${models_dir#$TARGET_ROOT/}"

    if [[ ! -f "$models_dir/__init__.py" ]]; then
        echo "Skipping $relative_models_dir: no Python __init__.py"
        continue
    fi

    echo
    echo "==> $relative_models_dir"
    for py in "${AVAILABLE_PYTHONS[@]}"; do
        echo "[$py] $models_dir"
        if ! (
            cd "$(dirname "$models_dir")" &&
            "$py" -m compileall models
        ); then
            FAILED=1
            echo "Failed: $py in $relative_models_dir" >&2
        fi
    done
done

exit "$FAILED"
