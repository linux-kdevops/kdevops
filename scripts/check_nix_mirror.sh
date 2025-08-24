#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

# Check for Nix cache mirror availability
NIX_CACHE_PATH="/mirror/nix-cache"
NIX_CACHE_PORT="8080"

# Function to check if mirror is available via HTTP
check_http_mirror() {
    local host=${1:-localhost}
    local port=${2:-$NIX_CACHE_PORT}

    # Try to reach the mirror HTTP endpoint
    if curl -s --connect-timeout 2 "http://${host}:${port}/status" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Function to check if mirror directory exists and has content
check_local_mirror() {
    if [[ -d "$NIX_CACHE_PATH" ]]; then
        # Check if directory has some cache files
        if find "$NIX_CACHE_PATH" -name "*.narinfo" -o -name "*.nar*" | head -1 | grep -q .; then
            return 0
        fi
        # Even if empty, the directory exists so mirror is configured
        return 0
    fi
    return 1
}

case "$1" in
    "USE_NIX_CACHE_MIRROR")
        # Check if we should use the mirror
        if check_local_mirror || check_http_mirror; then
            echo y
        else
            echo n
        fi
        ;;
    "NIX_CACHE_MIRROR_AVAILABLE")
        # Check if mirror is available (for client-side detection)
        if check_http_mirror; then
            echo y
        else
            echo n
        fi
        ;;
    "NIX_CACHE_MIRROR_URL")
        # Return the mirror URL if available
        if check_http_mirror localhost "$NIX_CACHE_PORT"; then
            echo "http://localhost:$NIX_CACHE_PORT"
        elif check_http_mirror "$(hostname -I | awk '{print $1}')" "$NIX_CACHE_PORT"; then
            echo "http://$(hostname -I | awk '{print $1}'):$NIX_CACHE_PORT"
        elif check_local_mirror; then
            # Use file:// URL for local directory-based cache
            echo "file://$NIX_CACHE_PATH"
        else
            echo ""
        fi
        ;;
    *)
        echo n
        ;;
esac
