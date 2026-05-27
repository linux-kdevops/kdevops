#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Merge defconfig fragments onto a base defconfig, expand the result with
# Kconfig defaults, and validate that every setting requested by a fragment
# actually survived into the final .config.
#
# Usage:
#   merge_defconfig_fragments.sh <conf> <base-defconfig> <fragment>...
#
# Fragment tokens are resolved, in order, to the first file that exists:
#   1. <dir>/<token>.config for each <dir> in $KDEVOPS_CONFIG_PATH
#      (colon separated, like $PATH)
#   2. ~/.config/kdevops/defconfigs/configs/<token>.config (user-private)
#   3. defconfigs/configs/<token>.config (in-tree)
#
# The $KDEVOPS_CONFIG_PATH search path lets users keep local, out-of-tree
# fragments (for PCIe passthrough devices, site-specific workflow setups, etc.)
# outside the kdevops repository while still composing them with shipped
# defconfigs. A path token cannot be passed through "make defconfig-<base>+..."
# because GNU make pattern rules split target names on '/'; use the search
# path instead.

set -e

if [ "$#" -lt 2 ]; then
	echo "usage: $0 <conf> <base-defconfig> <fragment>..." >&2
	exit 1
fi

CONF="$1"
BASE="$2"
shift 2

KCONFIG_CONFIG="${KCONFIG_CONFIG:-.config}"
MERGE_CONFIG_SH="$(dirname "$0")/merge_config.sh"
USER_CFG_DIR="$HOME/.config/kdevops/defconfigs/configs"

resolve_fragment() {
	local token="$1"
	local dir cand

	# Out-of-tree search path first, then the user-private dir, then in-tree.
	local IFS=:
	for dir in $KDEVOPS_CONFIG_PATH; do
		cand="$dir/$token.config"
		if [ -r "$cand" ]; then echo "$cand"; return 0; fi
	done
	unset IFS

	for dir in "$USER_CFG_DIR" "defconfigs/configs"; do
		cand="$dir/$token.config"
		if [ -r "$cand" ]; then echo "$cand"; return 0; fi
	done

	return 1
}

FRAG_FILES=""
for f in "$@"; do
	if ! resolved=$(resolve_fragment "$f"); then
		echo "Error: config fragment '$f' not found." >&2
		echo "Searched (in order): \$KDEVOPS_CONFIG_PATH, $USER_CFG_DIR, defconfigs/configs" >&2
		exit 1
	fi
	FRAG_FILES="$FRAG_FILES $resolved"
done

# Text-merge the base and fragments into the final config location. The base
# is a full kdevops defconfig, so we keep alldefconfig semantics (filling in
# unspecified symbols with their Kconfig defaults) by expanding with conf
# below rather than letting merge_config.sh run allnoconfig.
"$MERGE_CONFIG_SH" -m -Q "$BASE" $FRAG_FILES

# Snapshot the merged (override-resolved) request before expansion so that
# validation compares against what was actually asked for, not the raw
# per-fragment lines (a later fragment may legitimately override an earlier).
REQUESTED=$(mktemp ./.tmp.requested.XXXXXXXXXX)
trap 'rm -f "$REQUESTED"' EXIT
cp -- "$KCONFIG_CONFIG" "$REQUESTED"

# Expand with Kconfig defaults; this regenerates $KCONFIG_CONFIG.
"$CONF" --defconfig="$KCONFIG_CONFIG" Kconfig

# Validate that every symbol a fragment touched landed in the final config.
# A mismatch usually means an unmet dependency silently dropped the setting.
SED_SET='s/^\(CONFIG_[a-zA-Z0-9_]*\)=.*/\1/p'
SED_UNSET='s/^# \(CONFIG_[a-zA-Z0-9_]*\) is not set$/\1/p'

frag_syms=$(for frag in $FRAG_FILES; do
	sed -n -e "$SED_SET" -e "$SED_UNSET" "$frag"
done | sort -u)

mismatch=0
for cfg in $frag_syms; do
	requested=$(grep -w -e "$cfg" "$REQUESTED" | tail -1 || true)
	actual=$(grep -w -e "$cfg" "$KCONFIG_CONFIG" || true)
	if [ "$requested" != "$actual" ]; then
		if [ "$mismatch" = 0 ]; then
			echo "" >&2
			echo "Warning: fragment settings missing from $KCONFIG_CONFIG:" >&2
			mismatch=1
		fi
		echo "  $cfg" >&2
		echo "    requested: $requested" >&2
		echo "    actual:    ${actual:-(absent)}" >&2
	fi
done

if [ "$mismatch" = 1 ]; then
	echo "" >&2
	echo "A missing setting usually means an unmet dependency or an override" >&2
	echo "by a later fragment. Review the fragment and the generated config." >&2
fi

exit 0
