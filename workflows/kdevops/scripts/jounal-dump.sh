#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
# Collect guest remote journal logs from /var/log/journal/remote/

# Usage: ./collect-journals.sh <path-to-remote-journals> <ansible-inventory-file>
DIR=$1
INVENTORY=hosts
JOURNAL="journal"

mkdir -p journal

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <path-to-remote-journals>"
    exit 1
fi

# Get guest names from the Ansible inventory under the [all] group
GUESTS=$(awk '/\[all\]/ {getline; while ($0 !~ /^\[|^$/) {print $0; getline}}' $INVENTORY)

# Loop through each guest and collect journal files
for guest in $GUESTS; do
	echo $guest
    # Define the journal file path based on the guest
    JOURNAL_FILE="$DIR/remote-$guest.journal"

    if [[ -f $JOURNAL_FILE ]]; then
        # Output the journal file to an artifact-friendly file
        echo "Collecting journal for guest: $guest"
        journalctl --file="$JOURNAL_FILE" > "$JOURNAL/$guest.journal"
    else
        echo "No journal file found for guest: $guest"
    fi
done

echo "Journal collection complete."
