#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
Usage:
  run_odoo_sync_pipeline.sh [SOURCE_ROOT] [FINAL_TARGET]

Arguments:
  SOURCE_ROOT   Optional. If omitted, the script prompts for it.
  FINAL_TARGET  Optional. If omitted, the script prompts for it.

Environment:
  KEEP_INTERMEDIATES=1   Keep the temporary workspace instead of deleting it.
EOF
}

expand_home() {
    local path="$1"
    if [[ "$path" == "~" ]]; then
        printf '%s\n' "$HOME"
    elif [[ "$path" == ~/* ]]; then
        printf '%s\n' "$HOME/${path#~/}"
    else
        printf '%s\n' "$path"
    fi
}

run_step() {
    local label="$1"
    shift

    echo
    echo "==> $label"
    "$@"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

SOURCE_ROOT="${1:-}"
FINAL_TARGET="${2:-}"

if [[ -z "$SOURCE_ROOT" ]]; then
    read -r -p "Enter source directory: " SOURCE_ROOT
fi

SOURCE_ROOT="$(expand_home "$SOURCE_ROOT")"

if [[ -z "$SOURCE_ROOT" ]]; then
    echo "Source directory is required." >&2
    exit 1
fi

if [[ ! -d "$SOURCE_ROOT" ]]; then
    echo "Source add-ons root not found: $SOURCE_ROOT" >&2
    exit 1
fi

if [[ -z "$FINAL_TARGET" ]]; then
    read -r -p "Enter final target location: " FINAL_TARGET
fi

FINAL_TARGET="$(expand_home "$FINAL_TARGET")"

if [[ -z "$FINAL_TARGET" ]]; then
    echo "Final target location is required." >&2
    exit 1
fi

if ! command -v mktemp >/dev/null 2>&1; then
    echo "Required command not found: mktemp" >&2
    exit 1
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/odoo_sync_pipeline.XXXXXX")"
SPLITED_TARGET="$WORK_DIR/Odoo_sync_splited_script"
LEFT_TARGET="$WORK_DIR/Odoo_sync_compile_left_script"
COMPILED_TARGET="$WORK_DIR/Odoo_sync_compiled_script"

cleanup() {
    if [[ "${KEEP_INTERMEDIATES:-0}" == "1" ]]; then
        echo
        echo "Intermediate files kept at: $WORK_DIR"
        return
    fi
    rm -rf "$WORK_DIR"
}

trap cleanup EXIT

mkdir -p "$(dirname "$FINAL_TARGET")"

echo "Source root: $SOURCE_ROOT"
echo "Final target: $FINAL_TARGET"
echo "Workspace: $WORK_DIR"

run_step \
    "Transform base to splited" \
    "$SCRIPT_DIR/transform_base_to_splited.sh" \
    "$SOURCE_ROOT" \
    "$SPLITED_TARGET"

run_step \
    "Transform splited to compile_left" \
    "$SCRIPT_DIR/transform_splited_to_left.sh" \
    "$SPLITED_TARGET" \
    "$LEFT_TARGET"

run_step \
    "Compile models for all configured Python versions" \
    "$SCRIPT_DIR/compile_models_all_versions.sh" \
    "$LEFT_TARGET" \
    "$COMPILED_TARGET"

run_step \
    "Delete runtime model methods into final target" \
    "$SCRIPT_DIR/delete_model_methods.sh" \
    "$COMPILED_TARGET" \
    "$FINAL_TARGET"

echo
echo "Pipeline completed successfully."
echo "Final output: $FINAL_TARGET"
