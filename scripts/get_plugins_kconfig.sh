#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Returns the path to the plugins Kconfig file if it exists,
# otherwise returns the path to the stub file.
#
# This script is called by Kconfig's $(shell, ...) syntax to
# dynamically source installed plugin configurations.

PLUGINS_DIR="${HOME}/.config/kdevops/plugins"
PLUGINS_KCONFIG="${HOME}/.config/kdevops/Kconfig.plugins"
STUB_KCONFIG="kconfigs/Kconfig.plugins_stub"

if [ -f "${PLUGINS_KCONFIG}" ]; then
	echo "${PLUGINS_KCONFIG}"
else
	echo "${STUB_KCONFIG}"
fi
