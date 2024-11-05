#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
echo $1 | sha256sum | awk '{print $1}'
