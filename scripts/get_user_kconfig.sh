#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Returns the path to the user's Kconfig file if it exists,
# otherwise returns the path to the stub file.
#
# This script is called by Kconfig's $(shell, ...) syntax to
# dynamically source user-private workflow configurations.

USER_CONFIG_DIR="${HOME}/.config/kdevops"
USER_KCONFIG="${USER_CONFIG_DIR}/Kconfig"
STUB_KCONFIG="kconfigs/Kconfig.user_stub"

if [ -f "${USER_KCONFIG}" ]; then
	echo "${USER_KCONFIG}"
else
	echo "${STUB_KCONFIG}"
fi
