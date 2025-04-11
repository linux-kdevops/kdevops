# SPDX-License-Identifier: copyleft-next-0.3.1

REFS_DEFAULT_TARGETS := gen_refs_def_mainline
REFS_DEFAULT_TARGETS += gen_refs_def_next
REFS_DEFAULT_TARGETS += gen_refs_def_stable

KRELEASES_FORCE := $(if $(filter --force,$(KRELEASES_FORCE)),--force,)

ifeq ($(V),1)
KRELEASES_DEBUG = --debug
else
KRELEASES_DEBUG =
endif

gen_refs_def_mainline:
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/refs/default/Kconfig.linus \
		--extra workflows/linux/refs/static/linus.yaml \
		$(KRELEASES_FORCE) \
		$(KRELEASES_DEBUG) \
		kreleases \
		--moniker mainline \
		--pname $(PROJECT) \
		--pversion $(PROJECTVERSION)

gen_refs_def_next:
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/refs/default/Kconfig.next \
		--extra workflows/linux/refs/static/next.yaml \
		$(KRELEASES_FORCE) \
		$(KRELEASES_DEBUG) \
		kreleases \
		--moniker linux-next \
		--pname $(PROJECT) \
		--pversion $(PROJECTVERSION)

gen_refs_def_stable:
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/refs/default/Kconfig.stable \
		--extra workflows/linux/refs/static/stable.yaml \
		$(KRELEASES_FORCE) \
		$(KRELEASES_DEBUG) \
		kreleases \
		--moniker stable \
		--pname $(PROJECT) \
		--pversion $(PROJECTVERSION)

PHONY += refs-default
refs-default: $(REFS_DEFAULT_TARGETS) _gen-default-refs-development refs-user-clean

PHONY += _refs-default
_refs-default: $(REFS_DEFAULT_TARGETS)

PHONY += _refs-default-clean
_refs-default-clean:
	$(Q)rm --force workflows/linux/refs/default/Kconfig.linus
	$(Q)rm --force workflows/linux/refs/default/Kconfig.next
	$(Q)rm --force workflows/linux/refs/default/Kconfig.stable

.PHONY: $(PHONY)
