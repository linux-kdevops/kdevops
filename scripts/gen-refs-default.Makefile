# SPDX-License-Identifier: copyleft-next-0.3.1

REF_DEF_OBJS := $(addprefix $(TOPDIR)/workflows/linux/refs/default/, Kconfig.linus Kconfig.next Kconfig.stable)
REF_DEF_SRC  := $(addprefix $(TOPDIR)/workflows/linux/refs/static/,  linus.yaml next.yaml stable.yaml)

KRELEASES_FORCE := $(if $(filter --force,$(KRELEASES_FORCE)),--force,)

$(TOPDIR)/workflows/linux/refs/default/Kconfig.linus: $(TOPDIR)/workflows/linux/refs/static/linus.yaml
	$(Q)$(E) "Generating $@..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/refs/default/Kconfig.linus \
		--extra workflows/linux/refs/static/linus.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker mainline

$(TOPDIR)/workflows/linux/refs/default/Kconfig.next: $(TOPDIR)/workflows/linux/refs/static/next.yaml
	$(Q)$(E) "Generating $@..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/refs/default/Kconfig.next \
		--extra workflows/linux/refs/static/next.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker linux-next

$(TOPDIR)/workflows/linux/refs/default/Kconfig.stable: $(TOPDIR)/workflows/linux/refs/static/stable.yaml
	$(Q)$(E) "Generating $@..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/refs/default/Kconfig.stable \
		--extra workflows/linux/refs/static/stable.yaml \
		$(KRELEASES_FORCE) \
		kreleases \
		--moniker stable

PHONY += refs-default
refs-default: $(REF_DEF_OBJS) _gen-default-refs-development refs-user-clean

PHONY += _refs-default
_refs-default: $(REF_DEF_OBJS)

.PHONY: $(PHONY)
