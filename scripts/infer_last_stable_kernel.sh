#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

# This script infers the last stable kernel version from the git repository.
# It looks for the most recent non-rc tag (e.g., v6.14, v6.13) that would
# be a good default for A/B testing with different kernel references.

GIT_TREE="${1:-/mirror/linux.git}"

if [ ! -d "$GIT_TREE" ]; then
    echo "v6.12"  # fallback if no git tree available
    exit 0
fi

# Get all v6.x tags, excluding release candidates
# Sort them by version and get the last stable release
LAST_STABLE=$(git --git-dir="$GIT_TREE" tag --list 'v6.*' | \
    grep -v -- '-rc' | \
    sort -V | \
    tail -2 | head -1)

if [ -z "$LAST_STABLE" ]; then
    # If no stable v6.x found, try v5.x as fallback
    LAST_STABLE=$(git --git-dir="$GIT_TREE" tag --list 'v5.*' | \
        grep -v -- '-rc' | \
        sort -V | \
        tail -2 | head -1)
fi

# Final fallback if nothing found
if [ -z "$LAST_STABLE" ]; then
    echo "v6.12"
else
    echo "$LAST_STABLE"
fi
