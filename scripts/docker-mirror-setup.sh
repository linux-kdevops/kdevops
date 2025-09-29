#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Docker mirror setup script
# This script sets up a local Docker registry mirror for kdevops workflows

set -e

MIRROR_DIR="${1:-/mirror/docker}"
REGISTRY_PORT="${2:-5000}"
REGISTRY_NAME="${3:-kdevops-mirror}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or current user lacks permissions."
        exit 1
    fi
}

# Create mirror directory structure
setup_directories() {
    log_info "Setting up Docker mirror directories..."

    # Create main mirror directory
    if [ ! -d "$MIRROR_DIR" ]; then
        sudo mkdir -p "$MIRROR_DIR"
        log_info "Created $MIRROR_DIR"
    fi

    # Create subdirectories for registry data
    sudo mkdir -p "$MIRROR_DIR/registry"
    sudo mkdir -p "$MIRROR_DIR/images"
    sudo mkdir -p "$MIRROR_DIR/config"

    # Set appropriate permissions
    sudo chmod 755 "$MIRROR_DIR"
    sudo chmod 755 "$MIRROR_DIR/registry"
    sudo chmod 755 "$MIRROR_DIR/images"
    sudo chmod 755 "$MIRROR_DIR/config"

    log_info "Directory structure created successfully"
}

# Create registry configuration
create_registry_config() {
    log_info "Creating registry configuration..."

    cat > /tmp/docker-registry-config.yml << EOF
version: 0.1
log:
  fields:
    service: registry
storage:
  cache:
    blobdescriptor: inmemory
  filesystem:
    rootdirectory: /var/lib/registry
  delete:
    enabled: true
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
health:
  storagedriver:
    enabled: true
    interval: 10s
    threshold: 3
proxy:
  remoteurl: https://registry-1.docker.io
EOF

    sudo mv /tmp/docker-registry-config.yml "$MIRROR_DIR/config/config.yml"
    sudo chmod 644 "$MIRROR_DIR/config/config.yml"

    log_info "Registry configuration created"
}

# Start the Docker registry mirror
start_registry() {
    log_info "Starting Docker registry mirror..."

    # Check if registry is already running
    if docker ps -a | grep -q "$REGISTRY_NAME"; then
        log_warn "Registry container '$REGISTRY_NAME' already exists, removing it..."
        docker stop "$REGISTRY_NAME" 2>/dev/null || true
        docker rm "$REGISTRY_NAME" 2>/dev/null || true
    fi

    # Run the registry container
    docker run -d \
        --restart=always \
        --name "$REGISTRY_NAME" \
        -p "$REGISTRY_PORT:5000" \
        -v "$MIRROR_DIR/registry:/var/lib/registry" \
        -v "$MIRROR_DIR/config/config.yml:/etc/docker/registry/config.yml" \
        registry:2

    # Wait for registry to be ready
    log_info "Waiting for registry to be ready..."
    sleep 5

    if curl -s "http://localhost:$REGISTRY_PORT/v2/" > /dev/null; then
        log_info "Registry mirror is running on port $REGISTRY_PORT"
    else
        log_error "Failed to start registry mirror"
        exit 1
    fi
}

# Configure Docker daemon to use mirror
configure_docker_daemon() {
    log_info "Configuring Docker daemon to use mirror..."

    # Check if daemon.json exists
    DAEMON_CONFIG="/etc/docker/daemon.json"

    if [ -f "$DAEMON_CONFIG" ]; then
        log_warn "Docker daemon.json already exists, creating backup..."
        sudo cp "$DAEMON_CONFIG" "$DAEMON_CONFIG.bak.$(date +%Y%m%d_%H%M%S)"
    fi

    # Create or update daemon configuration
    cat > /tmp/docker-daemon.json << EOF
{
  "registry-mirrors": ["http://localhost:$REGISTRY_PORT"],
  "insecure-registries": ["localhost:$REGISTRY_PORT"]
}
EOF

    # If existing config exists, we need to merge
    if [ -f "$DAEMON_CONFIG" ]; then
        log_info "Merging with existing Docker daemon configuration..."
        # This is simplified - in production you'd want proper JSON merging
        log_warn "Manual merge may be required. New configuration saved to /tmp/docker-daemon.json"
    else
        sudo mv /tmp/docker-daemon.json "$DAEMON_CONFIG"
        sudo chmod 644 "$DAEMON_CONFIG"

        # Restart Docker daemon
        log_info "Restarting Docker daemon..."
        sudo systemctl restart docker
    fi
}

# Main execution
main() {
    log_info "Docker Mirror Setup for kdevops"
    log_info "==============================="

    check_docker
    setup_directories
    create_registry_config
    start_registry

    log_info ""
    log_info "Docker registry mirror setup complete!"
    log_info "Registry URL: http://localhost:$REGISTRY_PORT"
    log_info "Mirror directory: $MIRROR_DIR"
    log_info ""
    log_info "To configure Docker daemon to use this mirror, run:"
    log_info "  $0 --configure-daemon"
    log_info ""
    log_info "To pull and cache images, use the mirror-docker-images.sh script"
}

# Handle command line arguments
if [ "$1" == "--configure-daemon" ]; then
    configure_docker_daemon
    exit 0
fi

main "$@"
