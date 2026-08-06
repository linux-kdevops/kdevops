# pcie_uio

Runs Davidlohr Bueso's uio-tests harness for the PCIe Unordered I/O
(UIO) kernel RFC entirely on the controller (localhost). This is
PCI-SIG Unordered I/O, not the Linux userspace-I/O framework.

The harness boots eight emulated CXL/PCIe topologies itself under a
UIO-enumeration QEMU, so kdevops provisions no target nodes for this
workflow. The role:

- clones the kernel tree carrying the PCIe UIO series and the
  uio-tests harness (`pcie_uio_fetch`);
- builds a bzImage from the x86_64 defconfig plus the
  `files/pcie-uio-kernel.config` fragment, failing loudly when
  olddefconfig drops a required option (`pcie_uio_kernel`);
- downloads a Debian cloud qcow2 and customizes it once with
  virt-customize: root ssh key, DHCP on enp0s2, pciutils
  (`pcie_uio_image`);
- verifies /dev/kvm access and that the QEMU binary carries the
  `x-uio*` device knobs (`pcie_uio_check`);
- runs `run-all.sh`, collecting TAP + dmesg per suite plus the full
  transcript into the results directory (`pcie_uio_run`,
  `pcie_uio_results`).

The QEMU binary comes from the kdevops QEMU build support: enable
CONFIG_QEMU with CONFIG_QEMU_DAVIDLOHR_UIO (branch uio-work-rfc) and
the `qemu` make target; `qemu_bin_path` then points at the built
binary. A stock distro QEMU fails the knob probe with a clear message.

A green run validates the Linux control plane only — capability
discovery, typed P2PDMA providers, route objects, policy, revocation.
QEMU emulates UIO enumeration and route state; it moves no unordered
bytes on any wire, so never quote these results as UIO data-path or
performance evidence.

To refetch a tree after changing `pcie_uio_linux_ref` or
`pcie_uio_tests_ref`, remove the old checkout under `pcie_uio_data`
first: like the qemu role, fetches do not update an existing clone.
