# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Override fio to enable io_uring support via liburing and install
# the storage stack test suite, io_uring exerciser, and example
# job files that nixpkgs omits.
#
# nixpkgs fio (pkgs/by-name/fi/fio/package.nix) builds with libaio
# and libnbd but does not enable liburing or install t/io_uring,
# the Python NVMe test scripts, or the example .fio files.
final: prev: {
  fio = prev.fio.overrideAttrs (old: {
    buildInputs = (old.buildInputs or []) ++ [ final.liburing ];

    postInstall = (old.postInstall or "") + ''
      # t/io_uring: standalone io_uring and NVMe passthrough exerciser.
      # Not a fio self-test. Uses raw io_uring syscalls to benchmark
      # the kernel block layer. Fail the build if it is missing, since
      # liburing is now a declared buildInput.
      test -x t/io_uring
      install --mode=755 t/io_uring $out/bin/fio-io-uring

      # Storage stack test suite. Python scripts that validate kernel
      # NVMe features (FDP, DIF/DIX, streams, multi-range TRIM, ZBD)
      # using fio as the I/O generator.
      install --mode=755 --directory $out/share/fio/t
      install --mode=755 --directory $out/share/fio/t/zbd
      install --mode=644 t/*.py $out/share/fio/t/
      install --mode=755 t/one-core-peak.sh $out/share/fio/t/
      install --mode=755 t/zbd/* $out/share/fio/t/zbd/

      # Example job files.
      install --mode=755 --directory $out/share/doc/fio/examples
      install --mode=644 examples/*.fio $out/share/doc/fio/examples/
    '';
  });
}
