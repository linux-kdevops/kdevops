# SPDX-License-Identifier: GPL-2.0
#
# Simplified kconfig Makefile for subtree uses. This file is purposely
# maintained to be as simple as possible. The rest of the files in this
# directory are meant to match upstream.
#
# Part of the https://github.com/mcgrof/kconfig.git

CFLAGS := -Wall -Wmissing-prototypes -Wstrict-prototypes
CFLAGS += -O2 -fomit-frame-pointer
CFLAGS += -I ./
lxdialog        := $(addprefix lxdialog/, \
		checklist.o inputbox.o menubox.o textbox.o util.o yesno.o)

kconfig: conf mconf nconf

common-objs     := lexer.lex.o parser.tab.o confdata.o expr.o menu.o \
		   preprocess.o symbol.o util.o

lexer.lex.c: lexer.l parser.tab.h
	@flex -olexer.lex.c -L lexer.l

parser.tab.c parser.tab.h: parser.y
	@bison -oparser.tab.c --defines=parser.tab.h -t -l parser.y

conf: $(common-objs) conf.o
	$(CC) -o conf -I./ $^

HOSTLDLIBS_nconf       = $(call read-file, nconf-libs)
HOSTCFLAGS_nconf.o     = $(call read-file, nconf-cflags)
nconf: CFLAGS += ${HOSTCFLAGS_nconf.o}

HOSTLDLIBS_mconf = $(call read-file, mconf-libs)
$(foreach f, mconf.o $(lxdialog), \
  $(eval HOSTCFLAGS_$f = $$(call read-file, mconf-cflags)))
mconf: CFLAGS += ${HOSTCFLAGS_mconf.o}

export HOSTPKG_CONFIG := pkg-config
include $(CURDIR)/Kbuild.include
# check if necessary packages are available, and configure build flags
cmd_conf_cfg = $(CURDIR)/$< $(addprefix $*conf-, cflags libs bin); touch $*conf-bin

%conf-cflags %conf-libs %conf-bin: %conf-cfg.sh
	$(call cmd,conf_cfg)

MCONF_DEPS := $(common-objs) mconf.o $(lxdialog) mnconf-common.o
mconf:   | mconf-libs
mconf.o: | mconf-cflags
mconf: $(MCONF_DEPS) conf
	$(CC) -o mconf -I./ $(MCONF_DEPS) $(HOSTLDLIBS_mconf)

NCONF_DEPS := $(common-objs) nconf.o nconf.gui.o mnconf-common.o
nconf:   | nconf-libs
nconf.o: | nconf-cflags
nconf: $(NCONF_DEPS) conf
	$(CC) -o nconf $(NCONF_DEPS) $(HOSTLDLIBS_nconf)

clean-files := conf mconf nconf
clean-files += *.o lxdialog/*.o
clean-files += parser.tab.c parser.tab.h .lex.c
clean-files += *conf-cflags *conf-libs *conf-bin

.PHONY: help
help:
	@echo "Configuration options:"
	@echo "kconfig            - builds only requirements menuconfig and nconfig"
	@echo "menuconfig         - demos the menuconfig functionality"
	@echo "nconfig            - demos the nconfig functionality"
	@echo "allyesconfig       - enables all bells and whistles"
	@echo "allnoconfig        - disables all bells and whistles"
	@echo "randconfig         - random configuration"
	@echo "defconfig-*        - If you have files in the defconfig directory use default config from there"

.PHONY: clean
clean:
	@rm -f $(clean-files)
	@rm -rf *.o.d
