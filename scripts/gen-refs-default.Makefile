# SPDX-License-Identifier: copyleft-next-0.3.1

REFS_DEFAULT_TARGETS := gen_refs_def_mainline
REFS_DEFAULT_TARGETS += gen_refs_def_next
REFS_DEFAULT_TARGETS += gen_refs_def_stable
REF_DEF_SRC  := $(addprefix $(TOPDIR)/workflows/linux/refs/static/,  linus.yaml next.yaml stable.yaml)

KRELEASES_FORCE := $(if $(filter --force,$(KRELEASES_FORCE)),--force,)

gen_refs_def_mainline:
	$(Q)$(E) "Generating $@..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/refs/default/Kconfig.linus \
		--extra workflows/linux/refs/static/linus.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker mainline

gen_refs_def_next:
	$(Q)$(E) "Generating $@..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/refs/default/Kconfig.next \
		--extra workflows/linux/refs/static/next.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker linux-next

gen_refs_def_stable:
	$(Q)$(E) "Generating $@..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/refs/default/Kconfig.stable \
		--extra workflows/linux/refs/static/stable.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker stable

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
