# SPDX-License-Identifier: copyleft-next-0.3.1

AV ?= 0
export ANSIBLE_VERBOSE := $(shell scripts/validate_av.py --av "$(AV)")
