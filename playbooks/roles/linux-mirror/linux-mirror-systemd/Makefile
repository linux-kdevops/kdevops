USER_SYSTEM := ~/.config/systemd/user/
MIRROR_PATH := /mirror

ifeq (,$(wildcard $(TOPDIR_PATH)/.config))
else
include $(TOPDIR_PATH)/.config
endif

export BLKTESTS		:= $(subst ",,$(CONFIG_MIRROR_BLKTESTS_URL))

TOOLS_SERVICES  := blktests-mirror.service
TOOLS_TIMERS := blktests-mirror.timer

GIT_DAEMON_FILES := git-daemon@.service
GIT_DAEMON_FILES += git-daemon.socket
LOCAL_SYSTEMD    := /usr/local/lib/systemd/system/

BLKTESTS_TARGET		:= $(MIRROR_PATH)/blktests.git

MIRROR_SERVICES += $(TOOLS_SERVICES)
MIRROR_TIMERS   += $(TOOLS_TIMERS)

ifeq ($(V),1)
export Q=
export NQ=true
else
export Q=@
export NQ=@echo
endif

ifneq ($(findstring 2, $(V)),)
  export GIT_VERBOSE := "--verbose"
endif

all: help

help:
	$(NQ) "mirror:     git clone all mirrors"
	$(NQ) "install:    install system timers and git-daemon socket activation"

mirror:
	$(Q)if [ ! -d $(MIRROR_PATH) ]; then \
		mkdir -p $(MIRROR_PATH)     ;\
	fi
	$(NQ) "          Verify $(USER) can write onto $(MIRROR_PATH)"
	$(Q)touch $(MIRROR_PATH)/ignore_kdevops
	$(Q)rm -f $(MIRROR_PATH)/ignore_kdevops
	$(Q)if [ ! -d $(BLKTESTS_TARGET) ]; then \
	  echo "          CLONE blktests" ;\
	  git -C $(MIRROR_PATH) clone $(GIT_VERBOSE) --progress --mirror $(BLKTESTS) $(BLKTESTS_TARGET) ;\
	fi

install:
	$(Q)mkdir -p $(USER_SYSTEM)
	$(Q)cp $(MIRROR_SERVICES)   $(USER_SYSTEM)
	$(Q)cp $(MIRROR_TIMERS)     $(USER_SYSTEM)
	$(Q)for i in $(MIRROR_SERVICES); do           \
		echo  "Enabling $$i" ;                \
		systemctl --user enable  $$i ;        \
	done
	$(Q)for i in $(MIRROR_TIMERS); do             \
		echo  "Enabling $$i" ;                \
		systemctl --user enable $$i ;         \
		systemctl --user start $$i ;          \
	done
	$(NQ) "          ENABLE git-daemon"
	$(Q)sudo mkdir -p $(LOCAL_SYSTEMD)
	$(Q)sudo cp $(GIT_DAEMON_FILES) $(LOCAL_SYSTEMD)
	$(Q)sudo systemctl enable git-daemon.socket
	$(Q)sudo systemctl start git-daemon.socket

status:
	$(NQ) systemd timer units list
	$(Q)systemctl --user list-timers
	$(NQ) systemd timer status
	$(Q)systemctl status --user $(MIRROR_TIMERS)
	$(NQ) systemd service units status
	$(Q)systemctl status --user $(MIRROR_SERVICES)
