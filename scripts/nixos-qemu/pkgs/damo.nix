# SPDX-License-Identifier: copyleft-next-0.3.1
#
# DAMO: DAMON (Data Access MONitor) user-space tool.
#
# damo's upstream source layout is flat (src/*.py, no __init__.py).
# The packaging/ directory provides setup.py with console_scripts
# and package_dir={"": "src"}, but expects a src/damo/ package
# directory. The postPatch phase performs the same reorganization
# that Debian and packaging/build.sh do:
#
#   1. Copy packaging/pyproject.toml and packaging/setup.py to root
#   2. Create src/damo/ and move all .py files into it
#   3. Create src/damo/__init__.py
#
# Source: https://github.com/damonitor/damo
# Debian: https://packages.debian.org/trixie/damo
# Fedora: https://src.fedoraproject.org/rpms/python-damo
{ lib, python3Packages, fetchFromGitHub }:

python3Packages.buildPythonApplication rec {
  pname = "damo";
  version = "3.2.0";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "damonitor";
    repo = "damo";
    rev = "v${version}";
    hash = "sha256-DflgnU7/tepLwnDOOVahqsPXMSu0GJ/OWYnVd5qSCQA=";
  };

  # Reorganize flat src/*.py into a proper Python package at
  # src/damo/ so setuptools.find_packages(where="src") finds it.
  # This matches Debian's debian/rules execute_before_dh_auto_configure
  # and upstream's packaging/build.sh.
  postPatch = ''
    cp packaging/pyproject.toml pyproject.toml
    cp packaging/setup.py setup.py
    mkdir --parents src/damo
    cp src/*.py src/damo/
    touch src/damo/__init__.py
  '';

  build-system = [ python3Packages.setuptools ];

  # Pure Python, no runtime dependencies beyond the standard library.

  # Tests require a running kernel with CONFIG_DAMON enabled.
  doCheck = false;

  meta = {
    description = "DAMON user-space tool for data access monitoring";
    homepage = "https://github.com/damonitor/damo";
    license = lib.licenses.gpl2Only;
    platforms = lib.platforms.linux;
    mainProgram = "damo";
  };
}
