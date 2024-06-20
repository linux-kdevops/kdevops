# SPDX-License-Identifier: copyleft-next-0.3.1

REFS_TARGET_LNS := gen_default_refs_linus
REFS_TARGET_LNS += gen_default_refs_next
REFS_TARGET_LNS += gen_default_refs_stable

KRELEASES_FORCE := $(if $(filter --force,$(KRELEASES_FORCE)),--force,)

.PHONY += gen_default_refs_linus
gen_default_refs_linus:
	$(Q)$(E) "Generating refs/default/Kconfig.$(patsubst gen_default_refs_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/refs/default/Kconfig.linus \
		--extra workflows/linux/refs/static/linus.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker mainline

.PHONY += gen_default_refs_next
gen_default_refs_next:
	$(Q)$(E) "Generating refs/default/Kconfig.$(patsubst gen_default_refs_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/refs/default/Kconfig.next \
		--extra workflows/linux/refs/static/next.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker linux-next

.PHONY += gen_default_refs_stable
gen_default_refs_stable:
	$(Q)$(E) "Generating refs/default/Kconfig.$(patsubst gen_default_refs_%,%,$@)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/refs/default/Kconfig.stable \
		--extra workflows/linux/refs/static/stable.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker stable

_gen-default-refs-lns:
	$(Q)$(E) "Generating refs/default/Kconfig.{linus,next,stable} files..."
	$(Q)$(MAKE) $(REFS_TARGET_LNS) KRELEASES_FORCE="--force"

PHONY += refs-default
refs-default: _gen-default-refs-lns _gen-default-refs-development refs-user-clean

PHONY += _refs-default
_refs-default: _gen-default-refs-lns

.PHONY: $(PHONY)
