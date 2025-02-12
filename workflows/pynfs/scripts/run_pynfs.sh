#!/bin/bash

# Enable job control
set -m

vers=("4.0" "4.1")

flags=("all" "all deleg xattr")

# kick off jobs to run in the background in parallel
i=0
for version in "${vers[@]}"; do
	cd ${PYNFS_DATA}/nfs${version}
	./testserver.py --json="${PYNFS_DATA}/pynfs-${version}-results.json" --maketree --uid=0 --gid=0 "${EXPORT_BASE}-${version}" ${flags[$i]} &
	i=$((i + 1))
done

# wait for each to complete
for version in "${vers[@]}"; do
	fg || true
done
