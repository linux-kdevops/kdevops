# SPDX-License-Identifier: copyleft-next-0.3.1
#
# gitr workflow: git regression tests, the in-tree test suite
# shipped with git.git under t/.
#
# Upstream: https://github.com/git/git
#
# Git's own test suite shells out to Subversion and Mercurial for
# its foreign-SCM suites and exercises perl integration heavily;
# the suite expects gitFull rather than the minimal git package
# so perl bindings and gitweb support are available.
{ pkgs, ... }: {
  environment.systemPackages = with pkgs; [
    gitFull

    subversion
    mercurial

    perl
  ];
}
