#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Script to pull and cache Docker images for kdevops workflows
# This script can be run periodically to keep the mirror updated

set -e

MIRROR_DIR="${MIRROR_DIR:-/mirror/docker}"
REGISTRY_PORT="${REGISTRY_PORT:-5000}"
IMAGES_LIST="${1:-}"

# Default images used by kdevops workflows
DEFAULT_IMAGES=(
    # MinIO images
    "minio/minio:RELEASE.2023-03-20T20-16-18Z"

    # Milvus vector database images
    "milvusdb/milvus:2.3.0"
    "quay.io/coreos/etcd:v3.5.5"

    # vLLM standard deployment
    "vllm/vllm-openai:latest"

    # LMCache-enabled deployments (KV cache offloading, disaggregated prefill)
    "lmcache/vllm-openai:2025-05-27-v1"
    "lmcache/vllm-openai:latest-nightly"

    # Registry itself
    "registry:2"
)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Check if registry is running
check_registry() {
    if ! curl -s "http://localhost:$REGISTRY_PORT/v2/" > /dev/null 2>&1; then
        log_error "Docker registry mirror is not running on port $REGISTRY_PORT"
        log_info "Please run docker-mirror-setup.sh first"
        exit 1
    fi
}

# Pull and tag image for local registry
mirror_image() {
    local image="$1"
    local image_name="${image#*/}"  # Remove registry prefix if present
    local local_tag="localhost:$REGISTRY_PORT/$image_name"

    log_info "Mirroring $image..."

    # Pull from Docker Hub or original registry
    if docker pull "$image"; then
        log_info "Successfully pulled $image"

        # Tag for local registry
        docker tag "$image" "$local_tag"

        # Push to local registry
        if docker push "$local_tag"; then
            log_info "Successfully pushed to local registry: $local_tag"

            # Save image info to manifest
            echo "$image -> $local_tag" >> "$MIRROR_DIR/images/manifest.txt"
        else
            log_error "Failed to push $image to local registry"
            return 1
        fi
    else
        log_error "Failed to pull $image"
        return 1
    fi
}

# Save images to tar archives for offline use
save_image_archive() {
    local image="$1"
    local archive_dir="$MIRROR_DIR/images/archives"

    mkdir -p "$archive_dir"

    local image_file=$(echo "$image" | sed 's/[:/]/_/g').tar
    local archive_path="$archive_dir/$image_file"

    log_info "Saving $image to archive..."

    if docker save "$image" -o "$archive_path"; then
        # Compress the archive
        gzip -f "$archive_path"
        log_info "Saved and compressed: ${archive_path}.gz"

        # Generate checksum
        sha256sum "${archive_path}.gz" > "${archive_path}.gz.sha256"
    else
        log_error "Failed to save $image to archive"
        return 1
    fi
}

# Load custom images list from file
load_images_list() {
    local list_file="$1"

    if [ -f "$list_file" ]; then
        log_info "Loading images from $list_file"
        while IFS= read -r image; do
            # Skip comments and empty lines
            [[ "$image" =~ ^#.*$ ]] && continue
            [[ -z "$image" ]] && continue

            DEFAULT_IMAGES+=("$image")
        done < "$list_file"
    fi
}

# Scan kdevops configuration for Docker images
scan_for_images() {
    log_info "Scanning kdevops configuration for Docker images..."

    local found_images=()

    # Search for Docker image strings in ansible roles
    while IFS= read -r line; do
        if [[ "$line" =~ \"([^\"]+\/(.*):.*)\"|\'([^\']+\/(.*):.*)\' ]]; then
            local image="${BASH_REMATCH[1]}"
            if [ -z "$image" ]; then
                image="${BASH_REMATCH[3]}"
            fi
            if [ -n "$image" ] && [[ ! " ${found_images[@]} " =~ " ${image} " ]]; then
                found_images+=("$image")
                log_info "Found image: $image"
            fi
        fi
    done < <(grep -h "container_image\|docker_image" "$MIRROR_DIR/../playbooks/roles/"**/defaults/*.yml 2>/dev/null)

    # Add found images to the list
    for image in "${found_images[@]}"; do
        if [[ ! " ${DEFAULT_IMAGES[@]} " =~ " ${image} " ]]; then
            DEFAULT_IMAGES+=("$image")
        fi
    done
}

# Create manifest file
create_manifest() {
    local manifest_file="$MIRROR_DIR/images/manifest.txt"

    log_info "Creating manifest file..."

    echo "# Docker Images Mirror Manifest" > "$manifest_file"
    echo "# Generated: $(date)" >> "$manifest_file"
    echo "# Registry: localhost:$REGISTRY_PORT" >> "$manifest_file"
    echo "" >> "$manifest_file"
}

# Main execution
main() {
    log_info "Docker Images Mirror for kdevops"
    log_info "================================="

    check_registry

    # Create manifest
    mkdir -p "$MIRROR_DIR/images"
    create_manifest

    # Load custom images list if provided
    if [ -n "$IMAGES_LIST" ]; then
        load_images_list "$IMAGES_LIST"
    fi

    # Optionally scan for images
    if [ "$2" == "--scan" ]; then
        scan_for_images
    fi

    # Mirror all images
    local success=0
    local failed=0

    for image in "${DEFAULT_IMAGES[@]}"; do
        if mirror_image "$image"; then
            ((success++))

            # Optionally save to archive
            if [ "$2" == "--archive" ] || [ "$3" == "--archive" ]; then
                save_image_archive "$image"
            fi
        else
            ((failed++))
        fi
    done

    log_info ""
    log_info "Mirror operation complete!"
    log_info "Successfully mirrored: $success images"

    if [ $failed -gt 0 ]; then
        log_warn "Failed to mirror: $failed images"
    fi

    log_info ""
    log_info "Images are available at: localhost:$REGISTRY_PORT"
    log_info "Manifest file: $MIRROR_DIR/images/manifest.txt"

    if [ -d "$MIRROR_DIR/images/archives" ]; then
        log_info "Archive files: $MIRROR_DIR/images/archives/"
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 [images-list-file] [options]"
    echo ""
    echo "Options:"
    echo "  --scan      Scan kdevops configuration for Docker images"
    echo "  --archive   Save images to compressed tar archives"
    echo "  --help      Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  MIRROR_DIR      Mirror directory (default: /mirror/docker)"
    echo "  REGISTRY_PORT   Registry port (default: 5000)"
}

# Handle help option
if [ "$1" == "--help" ]; then
    show_usage
    exit 0
fi

main "$@"
