# SPDX-License-Identifier: copyleft-next-0.3.1

ansible-requirements:
	$(Q)ansible-galaxy install -r requirements.yml
PHONY += ansible-requirements
DEFAULT_DEPS += ansible-requirements
