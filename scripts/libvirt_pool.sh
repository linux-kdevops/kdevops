#!/bin/bash
# Helpers to work with virsh pools

get_can_sudo()
{
	# Heuristic to see if the current user can sudo
	# -n : This is the non-interactive argument in sudo and will prevent
	#      sudo from prompting the user for any kind of input.
	# -v : This tries to update the users cache credentials but also has
	#      distinct output for users with and without sudo:
	#      1. Without sudo the output is
	#         "Sorry, user __USER__ may not run sudo..."
	#      2. With sudo it has two messages: one for paswordless sudo and
	#         one passwordfull sudo. But we ignore the distinction as both
	#         of these mean that can_sudo is "y".
	if [[ $(sudo -nv 2>&1 | grep 'may not' > /dev/null) -eq 0 ]]; then
		echo "n"
		exit
	fi
	echo "y"
	exit
}

get_pool_vars()
{
	if [[ -f $OS_FILE ]]; then
		grep -qi fedora $OS_FILE
		if [[ $? -eq 0 ]]; then
			USES_QEMU_USER_SESSION="y"
		fi
	fi

	CAN_SUDO=get_can_sudo

	if [[ "$USES_QEMU_USER_SESSION" != "y" ]]; then
		REQ_SUDO="sudo"
	fi
}

virsh_works()
{
	if [[ "$USES_QEMU_USER_SESSION" == "n" && "$CAN_SUDO" != "y" ]]; then
		echo n
		return
	fi
	$REQ_SUDO which virsh 2>&1 > /dev/null
	if [[ $? -ne 0 ]]; then
		echo n
		return
	fi
	$REQ_SUDO virsh pool-list 2>&1 > /dev/null
	if [[ $? -eq 0 ]]; then
		echo y
	else
		echo n
	fi
}


virsh_get_pool_list()
{
	POOL_LIST=$($REQ_SUDO virsh pool-list| grep -E -v "Name|-----"|  sed -e '/^$/d' | awk '{print $1}')
}

virsh_path_in_pool_list_exists()
{
	for i in $POOL_LIST; do
		POOL_PATH=$($REQ_SUDO virsh pool-dumpxml $i | grep path | sed -e 's|<path>||'g | sed -e 's|</path>||'g | awk '{print $1}')
		echo $POOL_PATH | grep -q $BASE_DIR
		if [[ $? -eq 0 ]]; then
			echo y
			exit
		fi
	done
	echo n
}

virsh_path_pool_list_name()
{
	for i in $POOL_LIST; do
		POOL_PATH=$($REQ_SUDO virsh pool-dumpxml $i | grep path | sed -e 's|<path>||'g | sed -e 's|</path>||'g | awk '{print $1}')
		echo $POOL_PATH | grep -q $BASE_DIR
		if [[ $? -eq 0 ]]; then
			echo $i
			exit
		fi
	done
}

virsh_path_pool_list_path()
{
	for i in $POOL_LIST; do
		POOL_PATH=$($REQ_SUDO virsh pool-dumpxml $i | grep path | sed -e 's|<path>||'g | sed -e 's|</path>||'g | awk '{print $1}')
		echo $POOL_PATH | grep -q $BASE_DIR
		if [[ $? -eq 0 ]]; then
			echo $POOL_PATH
			exit
		fi
	done
}
