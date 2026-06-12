#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

# This script infers the last stable QEMU version from a local git mirror.
# It looks for the most recent vX.Y.Z release tag (excluding -rc tags) and
# echoes it, so the upstream QEMU build tracks the latest release instead of
# a stale pinned version. Mirrors scripts/infer_last_stable_kernel.sh.

GIT_TREE="${1:-/mirror/qemu.git}"

# Fallback used when no mirror is available (for example on a fresh checkout
# or in CI). Kept as a real, recent release rather than a release candidate.
FALLBACK="v10.0.0"

if [ ! -d "$GIT_TREE" ]; then
    echo "$FALLBACK"
    exit 0
fi

# List proper vX.Y.Z release tags, drop release candidates, sort by version
# and take the newest.
LAST_STABLE=$(git --git-dir="$GIT_TREE" tag --list 'v*' | \
    grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | \
    sort -V | \
    tail -1)

if [ -z "$LAST_STABLE" ]; then
    echo "$FALLBACK"
else
    echo "$LAST_STABLE"
fi
