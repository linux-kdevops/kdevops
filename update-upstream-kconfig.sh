#!/bin/bash

# This is what we use on the kconfig tree to sync to the latest linux-next
# kconfig from the Linux kernel.

UPSTREAM="$HOME/linux-next/"

KCONFIG_UPSTREAM="conf.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM confdata.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM expr.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM expr.h"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM internal.h"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM lkc.h"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM lkc_proto.h"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM lxdialog"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM mconf.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM mconf-cfg.sh"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM menu.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM mnconf-common.h"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM mnconf-common.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM nconf.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM nconf-cfg.sh"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM nconf.gui.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM nconf.h"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM preprocess.h"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM preprocess.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM symbol.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM util.c"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM lexer.l"
KCONFIG_UPSTREAM="$KCONFIG_UPSTREAM parser.y"

for i in $KCONFIG_UPSTREAM; do
	cp -a $UPSTREAM/scripts/kconfig/$i .
done

# We want to put everything we need for kconfig in the top level directory so to
# allow a project to just use kconfig in a sub tree, it will use this repo's top
# level directory and target its own scripts/kconfig directory.
KCONFIG_UPSTREAM_INC="list.h"
KCONFIG_UPSTREAM_INC="$KCONFIG_UPSTREAM_INC list_types.h"
KCONFIG_UPSTREAM_INC="$KCONFIG_UPSTREAM_INC hashtable.h"
KCONFIG_UPSTREAM_INC="$KCONFIG_UPSTREAM_INC array_size.h"
KCONFIG_UPSTREAM_INC="$KCONFIG_UPSTREAM_INC xalloc.h"

for i in $KCONFIG_UPSTREAM_INC; do
	cp -a $UPSTREAM/scripts/include/$i .
done

KCONFIG_UPSTREAM_LX="checklist.c"
KCONFIG_UPSTREAM_LX="$KCONFIG_UPSTREAM_LX  dialog.h"
KCONFIG_UPSTREAM_LX="$KCONFIG_UPSTREAM_LX  inputbox.c"
KCONFIG_UPSTREAM_LX="$KCONFIG_UPSTREAM_LX  menubox.c"
KCONFIG_UPSTREAM_LX="$KCONFIG_UPSTREAM_LX  textbox.c"
KCONFIG_UPSTREAM_LX="$KCONFIG_UPSTREAM_LX  util.c"
KCONFIG_UPSTREAM_LX="$KCONFIG_UPSTREAM_LX  yesno.c"

for i in $KCONFIG_UPSTREAM_LX; do
	cp -a $UPSTREAM/scripts/kconfig/lxdialog/$i lxdialog
done
