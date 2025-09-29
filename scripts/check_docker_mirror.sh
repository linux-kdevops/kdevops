#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Check if Docker mirror is available for kconfig defaults

DOCKER_MIRROR_PATH="${DOCKER_MIRROR_PATH:-/mirror/docker}"
REGISTRY_PORT="${DOCKER_REGISTRY_PORT:-5000}"

# Function to check if Docker registry is running
check_registry_running() {
    if command -v docker >/dev/null 2>&1; then
        docker ps --format "{{.Names}}" 2>/dev/null | grep -q "kdevops-docker-mirror"
        return $?
    fi
    return 1
}

# Function to check if registry is accessible
check_registry_accessible() {
    curl -s -f "http://localhost:${REGISTRY_PORT}/v2/" >/dev/null 2>&1
    return $?
}

# Main logic for kconfig
if [[ -d "$DOCKER_MIRROR_PATH" ]]; then
    case "$1" in
        ENABLE_DOCKER_MIRROR)
            echo "y"
            exit 0
            ;;

        USE_DOCKER_MIRROR)
            # Check if mirror has content and registry is accessible
            if [[ -d "$DOCKER_MIRROR_PATH/registry" ]]; then
                if check_registry_accessible; then
                    echo "y"
                    exit 0
                fi
            fi
            ;;

        INSTALL_DOCKER_MIRROR)
            # Check if this is first run (mirror exists but not fully configured)
            if [[ ! -d "$DOCKER_MIRROR_PATH/registry" ]]; then
                echo "y"
                exit 0
            fi
            # If registry exists but not running, suggest install
            if [[ -d "$DOCKER_MIRROR_PATH/registry" ]] && ! check_registry_running; then
                echo "y"
                exit 0
            fi
            ;;

        DOCKER_MIRROR_REGISTRY_RUNNING)
            if check_registry_running; then
                echo "y"
                exit 0
            fi
            ;;

        DOCKER_MIRROR_EXISTS|DOCKER_MIRROR_STATUS)
            # Provide user-friendly status output
            if [[ -d "$DOCKER_MIRROR_PATH" ]]; then
                echo "Docker mirror directory exists at $DOCKER_MIRROR_PATH"
                if check_registry_running; then
                    echo "Docker registry container is running"
                    if check_registry_accessible; then
                        echo "Docker registry is accessible at http://localhost:${REGISTRY_PORT}"
                    else
                        echo "Warning: Docker registry container is running but not accessible"
                    fi
                else
                    echo "Docker registry container is not running"
                    echo "Run 'make docker-mirror' to start the registry"
                fi
            else
                echo "Docker mirror not configured (directory $DOCKER_MIRROR_PATH does not exist)"
                echo "Run 'make docker-mirror' to set up the Docker mirror"
            fi
            exit 0
            ;;
    esac
fi

# Default to no for Kconfig checks
echo "n"
