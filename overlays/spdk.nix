# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Install the SPDK NVMe example exercisers nixpkgs builds but doesn't ship:
# cmb_copy (Controller Memory Buffer) and pmr_persistence (Persistent Memory
# Region), for testing emulated NVMe CMB/PMR from SPDK's userspace driver.
final: prev: {
  spdk = prev.spdk.overrideAttrs (prevAttrs: {
    # Prepend so the package's own postInstall rpath cleanup covers these too.
    postInstall = ''
      for ex in cmb_copy pmr_persistence; do
        test -x build/examples/$ex
        install --mode=755 build/examples/$ex $out/bin/spdk_nvme_$ex
      done
    ''
    + (prevAttrs.postInstall or "");
  });
}
