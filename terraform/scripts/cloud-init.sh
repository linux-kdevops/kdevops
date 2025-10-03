#!/bin/bash
# oscheck kdevops cloud-init script.
#
# This script accepts the following variables set and passed:
#
# user_data_log_dir
# user_data_enabled
#
# new_hostname
#
# Note: terraform passed variables must be in the form: dollar{variable},
# where dollar is $ and provides an implicit restriction on bash variables to
# not use this same form for bash variables *not* coming from terraform. This
# restriction applies even to bash comments such as this one. Terraform
# processes these variables prior to giving the file to the host. We cannot
# use this form of variables for user_data scripts then. Or another way to
# say it, terraform implicates restrictions on user_data bash scripts to
# only one way to use bash variables because of how it processes its own
# variables.
#
# Note 2: "let" returns non-zero if the argument passed is 0, use "let" to
# increment variables with care in your bash scripts if using "set -e"

ADMIN_LOG="${user_data_log_dir}/admin.txt"
USERDATA_ENABLED="${user_data_enabled}"

NEW_HOSTNAME="${new_hostname}"

set -e

run_cmd_admin()
{
        if $@ ; then
		DATE=$(date)
                echo "$DATE --- $@" >> $ADMIN_LOG
		return 0
        else
		DATE=$(date)
                echo "$DATE --- Return value: $? --- Command failed: $@ --- " >> $ADMIN_LOG
		return 1
        fi
}

mkdir -p ${user_data_log_dir}

if [ "$USERDATA_ENABLED" != "yes" ]; then
	run_cmd_admin echo "cloud-init: kdevops script user data processing disabled"
	exit 0
fi

run_cmd_admin echo "cloud-init: kdevops script user data processing enabled"

# Configure SSH port if not using default port 22
SSH_PORT="${ssh_config_port}"
if [ "$SSH_PORT" != "22" ]; then
	run_cmd_admin echo "Configuring SSH to listen on port $SSH_PORT"

	# Update sshd_config to use alternate port
	run_cmd_admin sed -i '/^[#[:space:]]*Port/d' /etc/ssh/sshd_config
	echo "Port $SSH_PORT" | run_cmd_admin tee -a /etc/ssh/sshd_config > /dev/null

	# Configure SELinux if present
	if [ -d /etc/selinux ] && sestatus 2>/dev/null | grep -q "SELinux status.*enabled"; then
		# Install semanage if not available (RHEL/CentOS/Rocky/AlmaLinux)
		if ! command -v semanage >/dev/null 2>&1; then
			run_cmd_admin yum install -y policycoreutils-python-utils 2>&1 || run_cmd_admin dnf install -y policycoreutils-python-utils 2>&1 || true
		fi

		# Try to add the port first, if it fails (already exists), modify it
		if command -v semanage >/dev/null 2>&1; then
			run_cmd_admin semanage port -a -t ssh_port_t -p tcp $SSH_PORT 2>&1 || run_cmd_admin semanage port -m -t ssh_port_t -p tcp $SSH_PORT 2>&1 || true
			run_cmd_admin echo "SELinux port configuration completed"
		else
			run_cmd_admin echo "WARNING: semanage not available, SELinux may block port $SSH_PORT"
		fi
	fi

	# Configure firewalld if present and enabled
	if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-enabled firewalld >/dev/null 2>&1; then
		run_cmd_admin firewall-cmd --permanent --add-port=$SSH_PORT/tcp
		run_cmd_admin firewall-cmd --reload
	fi

	# Configure ufw if present and active
	if command -v ufw >/dev/null 2>&1 && systemctl is-active ufw >/dev/null 2>&1; then
		run_cmd_admin ufw allow $SSH_PORT/tcp
	fi

	# Restart sshd to apply changes
	run_cmd_admin systemctl restart sshd
	run_cmd_admin echo "SSH port configuration completed"
else
	run_cmd_admin echo "Using default SSH port 22, no configuration needed"
fi

# Add more functionality below if you see fit. Be sure to use a variable
# to allow to easily enable / disable each mechanism.
