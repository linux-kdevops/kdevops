# Docker Mirror Images Directory

This directory contains **configuration files only**, not actual Docker images.

## Directory Purpose

- `workflow-images.txt` - List of Docker images to be mirrored/cached
- Additional workflow-specific image lists may be added here

## Where Are The Actual Images?

The actual Docker images are stored in:
- **Compressed tarballs**: `../registry/tarballs/` (for non-Docker Hub images)
- **Registry cache**: `../registry/` (for Docker Hub pull-through cache)

## Why This Directory Exists

This directory serves as a configuration point to specify which images should be:
1. Downloaded and cached locally
2. Made available for offline/air-gapped environments
3. Periodically updated via systemd timers

## Important Note

If you're looking for actual Docker images, check:
```bash
# List downloaded image tarballs
ls -lh ../registry/tarballs/

# Load a specific image
gunzip -c ../registry/tarballs/<image>.tar.gz | docker load
```

This separation keeps configuration manageable while storing the actual multi-GB image data elsewhere.
