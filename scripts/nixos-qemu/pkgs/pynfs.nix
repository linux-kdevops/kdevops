# SPDX-License-Identifier: copyleft-next-0.3.1
#
# pynfs: Python NFSv4 conformance test suite covering NFSv4.0,
# NFSv4.1, and pNFS block layouts with Kerberos bindings.
#
# The top-level setup.py delegates to 4 sub-packages (xdr, rpc,
# nfs4.1, nfs4.0). pip cannot handle this; we use setup.py directly.
# The build includes SWIG-generated Kerberos bindings (compiled C).
#
# No formal releases exist. We pin to a commit.
#
# Source: https://github.com/ffilz/pynfs
{
  lib,
  python3Packages,
  fetchFromGitHub,
  swig,
  krb5,
}:

python3Packages.buildPythonApplication rec {
  pname = "pynfs";
  version = "unstable-2025-03-05";
  pyproject = false;

  src = fetchFromGitHub {
    owner = "ffilz";
    repo = "pynfs";
    rev = "d3a1610815117cb6bdf6567e575baedb0d88095e";
    hash = "sha256-grigxIDAQG4hnwA/YmsHNP3aKX61uw76I/ClgT0+u8Q=";
  };

  nativeBuildInputs = [
    swig
    krb5.dev
    python3Packages.setuptools
  ];

  buildInputs = [ krb5 ];

  dependencies = with python3Packages; [
    gssapi
    ply
  ];

  # Upstream uses distutils which was removed in Python 3.12.
  # Patch to use setuptools instead.
  postPatch = ''
    substituteInPlace setup.py \
      --replace-fail 'from distutils.core import setup' \
                     'from setuptools import setup'
    for f in xdr/setup.py rpc/setup.py nfs4.1/setup.py nfs4.0/setup.py; do
      if [ -f "$f" ]; then
        substituteInPlace "$f" \
          --replace-fail 'from distutils.core import setup' \
                         'from setuptools import setup'
      fi
    done
  '';

  # The delegating setup.py handles all 4 sub-packages.
  buildPhase = ''
    runHook preBuild
    python setup.py build
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    python setup.py install --prefix=$out --optimize=1

    # The delegating setup.py installs libraries but not scripts.
    # Install the test runners from the sub-packages manually.
    mkdir --parents $out/bin
    install --mode=755 nfs4.0/testserver.py $out/bin/nfs4-testserver
    install --mode=755 nfs4.0/showresults.py $out/bin/nfs4-showresults
    if [ -f nfs4.1/testserver.py ]; then
      install --mode=755 nfs4.1/testserver.py $out/bin/nfs41-testserver
    fi

    # Patch shebangs.
    patchShebangs $out/bin
    runHook postInstall
  '';

  doCheck = false;

  meta = {
    description = "Python NFSv4 conformance test suite";
    homepage = "https://github.com/ffilz/pynfs";
    license = lib.licenses.gpl2Only;
    platforms = lib.platforms.linux;
  };
}
