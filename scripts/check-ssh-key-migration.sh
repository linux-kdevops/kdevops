#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Check if SSH keys need migration from old (unhashed) to new (hashed) paths.
# This helps users upgrading from older kdevops versions that used a fixed
# SSH key path to the new per-directory hashed paths.

set -e

TOPDIR_PATH="${1:-.}"
HASH=$(echo "$TOPDIR_PATH" | sha256sum | cut -c1-8)

OLD_KEY="$HOME/.ssh/kdevops_terraform"
OLD_PUBKEY="$HOME/.ssh/kdevops_terraform.pub"
NEW_KEY="$HOME/.ssh/kdevops_terraform_${HASH}"
NEW_PUBKEY="$HOME/.ssh/kdevops_terraform_${HASH}.pub"

# Only show notice if old key exists but new key doesn't
if [ -f "$OLD_PUBKEY" ] && [ ! -f "$NEW_PUBKEY" ]; then
	cat <<EOF
--------------------------------------------------------------------------------
NOTE: SSH key path has changed

kdevops now uses directory-specific SSH key paths. An old-style key exists:
  Old: $OLD_PUBKEY
  New: $NEW_PUBKEY

If you have RUNNING VMs that need the old key, migrate it:
  mv "$OLD_KEY" "$NEW_KEY"
  mv "$OLD_PUBKEY" "$NEW_PUBKEY"

Otherwise, a new key will be generated automatically.
--------------------------------------------------------------------------------
EOF
fi
