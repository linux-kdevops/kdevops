#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

version="4.1"

cd ${PYNFS_DATA}/nfs${version}
./testserver.py --json="${PYNFS_DATA}/pynfs-block-results.json" --maketree --uid=0 --gid=0 "${EXPORT_BASE}-pnfs" block
