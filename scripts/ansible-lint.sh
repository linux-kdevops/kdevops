#!/usr/bin/env bash
# SPDX-License-Identifier: copyleft-next-0.3.1
set -euxo pipefail

ansible-lint playbooks/*.yml --exclude playbooks/roles/
