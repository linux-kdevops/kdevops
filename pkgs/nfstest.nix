# SPDX-License-Identifier: copyleft-next-0.3.1
#
# NFStest: NFS test suite covering space reservation, direct I/O,
# interoperability, file locking, POSIX compliance, sparse files,
# and server-side copy.
#
# The upstream setup.py tries to generate manpages during build by
# running installed scripts, which fails before install. Patch it
# out so the build completes without running uninstalled scripts.
#
# Source: git://linux-nfs.org/projects/mora/nfstest
{
  lib,
  python3Packages,
  fetchurl,
  nfs-utils,
  tcpdump,
}:

python3Packages.buildPythonApplication rec {
  pname = "nfstest";
  version = "3.2";
  pyproject = false;

  src = fetchurl {
    url = "https://www.linux-nfs.org/~mora/nfstest/releases/NFStest-${version}.tar.gz";
    hash = "sha256-TUxcWttygx9Xhyde8jxUFP9cV84SDK+xzVPeB2ZXRcE=";
  };

  postPatch = ''
    # Disable manpage generation during build. The setup.py build
    # command runs installed scripts with --version/--help which
    # fails before install.
    substituteInPlace setup.py \
      --replace-fail 'create_manpage.run()' 'pass'

    # Replace distutils with setuptools (distutils removed in 3.12).
    substituteInPlace setup.py \
      --replace-fail 'from distutils.core import setup' \
                     'from setuptools import setup' \
      --replace-fail 'from distutils.command.build import build' \
                     'from setuptools.command.build import build'
  '';

  # pyproject = false, so the legacy setup.py path is used; pip
  # drives the install in installPhase below. build-system still
  # seeds setuptools into the build environment even on the legacy
  # path, so pip can import setuptools.build_meta.
  nativeBuildInputs = [ python3Packages.pip ];
  build-system = [ python3Packages.setuptools ];

  buildPhase = ''
    runHook preBuild
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    pip install --prefix=$out --no-deps --no-build-isolation .
    patchShebangs $out/bin
    runHook postInstall
  '';

  # Pure Python, no compiled extensions.
  doCheck = false;

  # nfs-utils (mount.nfs) and tcpdump (packet capture) are runtime
  # CLI tools, not Python dependencies — put them on the wrapped
  # scripts' PATH rather than in the propagated closure.
  makeWrapperArgs = [
    "--prefix"
    "PATH"
    ":"
    (lib.makeBinPath [
      nfs-utils
      tcpdump
    ])
  ];

  meta = {
    description = "NFS test suite for Linux";
    homepage = "https://www.linux-nfs.org/~mora/nfstest/";
    license = lib.licenses.gpl2Only;
    platforms = lib.platforms.linux;
    mainProgram = "nfstest_posix";
    maintainers = [ ];
  };
}
