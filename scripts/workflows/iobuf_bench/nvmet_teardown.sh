#!/bin/bash
# nvmet_teardown.sh -- remove the kernel NVMe-oF/TCP target config.
CFG=/sys/kernel/config/nvmet
PORT=$CFG/ports/1
for l in $PORT/subsystems/*; do [ -e "$l" ] && sudo rm -f "$l"; done
for sub in $CFG/subsystems/nvmet-bench-*; do
  [ -d "$sub" ] || continue
  echo 0 | sudo tee $sub/namespaces/1/enable >/dev/null 2>&1
  sudo rmdir $sub/namespaces/1 2>/dev/null
  sudo rmdir $sub 2>/dev/null
done
sudo rmdir $PORT 2>/dev/null
echo "nvmet-tcp torn down"
