#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

# Part of kdevops reboot-limit loop testing, this script will run the test workflow
# as many times as indicated up to CONFIG_REBOOT_LIMIT_LOOP_STEADY_STATE_GOAL

source ${TOPDIR}/.config
source ${TOPDIR}/scripts/lib.sh

# Check if we're resuming from a previous run
if [[ "$CONFIG_REBOOT_LIMIT_LOOP_STEADY_STATE_INCREMENTAL" == "y" && -f $KERNEL_CI_OK_FILE ]]; then
	COUNT=$(cat $KERNEL_CI_OK_FILE)
	let COUNT=$COUNT+1
else
	COUNT=1
	rm -f $KERNEL_CI_OK_FILE
fi

run_loop()
{
	while true; do
		echo "== reboot-limit test loop $COUNT start: $(date)" > $KERNEL_CI_FAIL_LOG
		echo "/usr/bin/time -f %E make reboot-limit-baseline" >> $KERNEL_CI_FAIL_LOG
		/usr/bin/time -p -o $KERNEL_CI_LOGTIME make reboot-limit-baseline >> $KERNEL_CI_FAIL_LOG
		ANSIBLE_CALL_RET=$?
		echo "End   $COUNT: $(date)" >> $KERNEL_CI_FAIL_LOG
		cat $KERNEL_CI_LOGTIME >> $KERNEL_CI_FAIL_LOG
		echo "git status:" >> $KERNEL_CI_FAIL_LOG
		git status >> $KERNEL_CI_FAIL_LOG
		echo "Results:" >> $KERNEL_CI_FAIL_LOG

		rm -f $KERNEL_CI_DIFF_LOG

		if [[ "$ANSIBLE_CALL_RET" -ne 0 ]]; then
			echo "Test  $COUNT: FAILED!" >> $KERNEL_CI_DIFF_LOG
			echo "== Test loop count $COUNT" >> $KERNEL_CI_DIFF_LOG
			echo "$(git describe)" >> $KERNEL_CI_DIFF_LOG
			git diff >> $KERNEL_CI_DIFF_LOG
			cat $KERNEL_CI_DIFF_LOG >> $KERNEL_CI_FAIL_LOG
			cat $KERNEL_CI_FAIL_LOG >> $KERNEL_CI_FULL_LOG
			echo $COUNT > $KERNEL_CI_FAIL_FILE
			exit 1
		else
			echo "Test  $COUNT: OK!" >> $KERNEL_CI_FAIL_LOG
			echo "----------------------------------------------------------------" >> $KERNEL_CI_FAIL_LOG
			cat $KERNEL_CI_FAIL_LOG >> $KERNEL_CI_FULL_LOG
		fi

		# This let's us keep track of hich loop count was last successful
		echo $COUNT > $KERNEL_CI_OK_FILE

		let COUNT=$COUNT+1
		if [[ "$CONFIG_REBOOT_LIMIT_ENABLE_LOOP" == "y" &&
		      "$COUNT" -gt "$CONFIG_REBOOT_LIMIT_LOOP_STEADY_STATE_GOAL" ]]; then
			exit 0
		fi
		sleep 1
	done
}

rm -f $KERNEL_CI_FAIL_FILE
echo "= reboot-limit loop full log" > $KERNEL_CI_FULL_LOG
run_loop
