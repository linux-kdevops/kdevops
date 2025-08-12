#!/bin/bash
# Script to apply mmtests patches with proper error handling

TOPDIR="$1"
PATCH_FILE="$2"

cd "$TOPDIR/tmp/mmtests" || exit 1

PATCH_NAME=$(basename "$PATCH_FILE")

# Check if patch is already applied by looking for the specific fix
if grep -q "if (@operations > 0 && exists" bin/lib/MMTests/Compare.pm 2>/dev/null; then
    echo "Patch $PATCH_NAME appears to be already applied"
    exit 0
fi

# Try to apply with git apply first
if git apply --check "$PATCH_FILE" 2>/dev/null; then
    git apply "$PATCH_FILE"
    echo "Applied patch with git: $PATCH_NAME"
    exit 0
fi

# Try with patch command as fallback
if patch -p1 --dry-run < "$PATCH_FILE" >/dev/null 2>&1; then
    patch -p1 < "$PATCH_FILE"
    echo "Applied patch with patch command: $PATCH_NAME"
    exit 0
fi

echo "Failed to apply $PATCH_NAME - may already be applied or conflicting"
exit 0  # Don't fail the playbook
