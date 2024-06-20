# SPDX-License-Identifier: copyleft-next-0.3.1

ifeq ($(V),1)
export Q=@
export E=echo
else
export Q=@
export E=true
endif

include scripts/gen-refs-default.Makefile
include scripts/gen-refs-user.Makefile

PHONY += refs-help-menu
refs-help-menu:
	@echo "Generate git references options"
	@echo "refs-default   - Switch to Git Reference Default Mode"
	@echo "refs-user      - Switch to Git Reference User Mode"
	@echo ""

HELP_TARGETS += refs-help-menu
.PHONY = $(PHONY)
