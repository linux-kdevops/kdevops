# SPDX-License-Identifier: copyleft-next-0.3.1

SRC_URI_HTTPS_LINUS = https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
SRC_URI_HTTPS_NEXT = https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git
SRC_URI_HTTPS_STABLE = https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git

SRC_URI_HTTPS_MCGROF_LINUS = https://git.kernel.org/pub/scm/linux/kernel/git/mcgrof/linux.git
SRC_URI_HTTPS_MCGROF_NEXT = https://git.kernel.org/pub/scm/linux/kernel/git/mcgrof/linux-next.git
SRC_URI_HTTPS_BTRFS_DEVEL = https://github.com/kdave/btrfs-devel.git
SRC_URI_HTTPS_CEL_LINUX = https://git.kernel.org/pub/scm/linux/kernel/git/cel/linux.git
SRC_URI_HTTPS_JLAYTON_LINUX = https://git.kernel.org/pub/scm/linux/kernel/git/jlayton/linux.git
SRC_URI_HTTPS_KDEVOPS_LINUS = https://github.com/linux-kdevops/linux.git

REFS_TARGET_LINUS := gen_refs_linus
REFS_TARGET_NEXT := gen_refs_next
REFS_TARGET_STABLE := gen_refs_stable

REFS_TARGET_DEVELOPMENT := gen_refs_mcgrof_linus
REFS_TARGET_DEVELOPMENT += gen_refs_mcgrof_next
REFS_TARGET_DEVELOPMENT += gen_refs_btrfs_devel
REFS_TARGET_DEVELOPMENT += gen_refs_cel_linux
REFS_TARGET_DEVELOPMENT += gen_refs_jlayton_linux
REFS_TARGET_DEVELOPMENT += gen_refs_kdevops_linus

REFS_COUNT := 15
UREF_EXT ?= uref-

PHONY += gen_refs_linus
gen_refs_linus:
	$(Q)$(E) "Generating refs/$(REFS_DIR)/Kconfig.$(subst _,-,$(patsubst gen_refs_%,%,$@)) ($(REFS_COUNT) refs)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_LINUS \
		--output workflows/linux/refs/$(REFS_DIR)/Kconfig.linus \
		--extra workflows/linux/refs/static/linus.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_LINUS) \
		--refs $(REFS_COUNT)

PHONY += gen_refs_next
gen_refs_next:
	$(Q)$(E) "Generating refs/$(REFS_DIR)/Kconfig.$(subst _,-,$(patsubst gen_refs_%,%,$@)) ($(REFS_COUNT) refs)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_NEXT \
		--output workflows/linux/refs/$(REFS_DIR)/Kconfig.next \
		--extra workflows/linux/refs/static/next.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_NEXT) \
		--refs $(REFS_COUNT) \
		--filter-tags next* \

PHONY += gen_refs_stable
gen_refs_stable:
	$(Q)$(E) "Generating refs/$(REFS_DIR)/Kconfig.$(subst _,-,$(patsubst gen_refs_%,%,$@)) ($(REFS_COUNT) refs)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_STABLE \
		--output workflows/linux/refs/$(REFS_DIR)/Kconfig.stable \
		--extra workflows/linux/refs/static/stable.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_STABLE) \
		--refs $(REFS_COUNT)

PHONY += gen_refs_mcgrof_linus
gen_refs_mcgrof_linus:
	$(Q)$(E) "Generating refs/$(REFS_DIR)/Kconfig.$(subst _,-,$(patsubst gen_refs_%,%,$@)) ($(REFS_COUNT) refs)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_MCGROF_LINUS \
		--output workflows/linux/refs/$(REFS_DIR)/Kconfig.mcgrof-linus \
		--extra workflows/linux/refs/static/mcgrof-linus.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_MCGROF_LINUS) \
		--refs $(REFS_COUNT)

PHONY += gen_refs_mcgrof_next
gen_refs_mcgrof_next:
	$(Q)$(E) "Generating refs/$(REFS_DIR)/Kconfig.$(subst _,-,$(patsubst gen_refs_%,%,$@)) ($(REFS_COUNT) refs)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_MCGROF_NEXT \
		--output workflows/linux/refs/$(REFS_DIR)/Kconfig.mcgrof-next \
		--extra workflows/linux/refs/static/mcgrof-next.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_MCGROF_NEXT) \
		--refs $(REFS_COUNT)

PHONY += gen_refs_btrfs_devel
gen_refs_btrfs_devel:
	$(Q)$(E) "Generating refs/$(REFS_DIR)/Kconfig.$(subst _,-,$(patsubst gen_refs_%,%,$@)) ($(REFS_COUNT) refs)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_BTRFS_DEVEL \
		--output workflows/linux/refs/$(REFS_DIR)/Kconfig.btrfs-devel \
		--extra workflows/linux/refs/static/btrfs-devel.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_BTRFS_DEVEL) \
		--refs $(REFS_COUNT)

PHONY += gen_refs_cel_linux
gen_refs_cel_linux:
	$(Q)$(E) "Generating refs/$(REFS_DIR)/Kconfig.$(subst _,-,$(patsubst gen_refs_%,%,$@)) ($(REFS_COUNT) refs)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_CEL_LINUX \
		--output workflows/linux/refs/$(REFS_DIR)/Kconfig.cel-linux \
		--extra workflows/linux/refs/static/cel-linux.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_CEL_LINUX) \
		--refs $(REFS_COUNT)

PHONY += gen_refs_jlayton_linux
gen_refs_jlayton_linux:
	$(Q)$(E) "Generating refs/$(REFS_DIR)/Kconfig.$(subst _,-,$(patsubst gen_refs_%,%,$@)) ($(REFS_COUNT) refs)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_JLAYTON_LINUX \
		--output workflows/linux/refs/$(REFS_DIR)/Kconfig.jlayton-linux \
		--extra workflows/linux/refs/static/jlayton-linux.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_JLAYTON_LINUX) \
		--refs $(REFS_COUNT)

PHONY += gen_refs_kdevops_linus
gen_refs_kdevops_linus:
	$(Q)$(E) "Generating refs/$(REFS_DIR)/Kconfig.$(subst _,-,$(patsubst gen_refs_%,%,$@)) ($(REFS_COUNT) refs)..."
	$(Q)./scripts/generate_refs.py \
		--prefix BOOTLINUX_TREE_KDEVOPS_LINUS \
		--output workflows/linux/refs/$(REFS_DIR)/Kconfig.kdevops-linus \
		--extra workflows/linux/refs/static/kdevops-linus.yaml \
		--force \
		gitref \
		--repo $(SRC_URI_HTTPS_KDEVOPS_LINUS) \
		--refs $(REFS_COUNT)

PHONY += refs-user-clean
refs-user-clean:
	$(Q)if [ -d workflows/linux/refs/user ]; then \
		find workflows/linux/refs/user -iname 'Kconfig.*' -exec truncate --size 0 {} \;; \
	fi

_gen-user-refs:
	$(Q)$(E) "Generating refs/user/Kconfig.{linus,next,stable,mcgrof-linus,mcgrof-next,btrfs-devel,cel-linux-jlayton-linux-kdevops-linus} files..."
	$(Q)$(MAKE) REFS_COUNT=15 REFS_DIR="user" $(REFS_TARGET_LINUS) $(REFS_TARGET_NEXT) $(REFS_TARGET_STABLE) $(REFS_TARGET_DEVELOPMENT)

PHONY += refs-user
refs-user: _gen-user-refs

_gen-default-refs-development:
	$(Q)$(E) "Generating refs/default/Kconfig-{mcgrof-linus,mcgrof-next,btrfs-devel,cel-linux-jlayton-linux-kdevops-linus} files..."
	$(Q)$(MAKE) REFS_COUNT=0 REFS_DIR="default" $(REFS_TARGET_DEVELOPMENT)

.PHONY: $(PHONY)
