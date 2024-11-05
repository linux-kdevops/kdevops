# SPDX-License-Identifier: copyleft-next-0.3.1

DEFCONFIGS := $(notdir $(wildcard defconfigs/*))

$(foreach cfg,$(DEFCONFIGS),$(eval defconfig-$(cfg): defconfigs/$(cfg)))

defconfig-%: $(KCONFIG_DIR)/conf Kconfig
	scripts/conf --defconfig=defconfigs/$* Kconfig
