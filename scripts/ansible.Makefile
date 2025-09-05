# SPDX-License-Identifier: copyleft-next-0.3.1

AV ?= 0
export ANSIBLE_VERBOSE := $(shell scripts/validate_av.py --av "$(AV)")

ansible-requirements:
	$(Q)ansible-galaxy install -r requirements.yml
PHONY += ansible-requirements
DEFAULT_DEPS += ansible-requirements
