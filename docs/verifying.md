# Verifying changes

Run these steps before every commit. They are manual for now; whether
and how to wire them as git hooks is a later decision. Each step states
why it exists and what it does.

## 1. Format — `nix fmt`

Why: the whole history is `nixfmt-rfc-style`-clean; a commit that drifts
breaks that invariant.

What: rewrites every `.nix` file in place to the canonical style. Run
`git diff` afterwards — a non-empty diff means your change introduced
unformatted code; stage the reformat.

## 2. Evaluate and build the system closures — `nix flake check`

Why: catches evaluation errors, broken module options, and malformed
flake outputs, and proves each backend still produces a valid NixOS
system. Also exercises every test-suite module composed on top of the
imageless backend, the user account, and monitoring — the realistic
shape a consumer deploys.

What: evaluates every flake output and builds
`checks.<system>.{imageless,libvirt,controller,imageless-<suite>}`
— the three base closures and one closure per test-suite module. The
first run builds them all; later runs are cached. Add `--all-systems`
to also cover `aarch64-linux` (needs an aarch64 builder).

## 3. Build the templates

Why: step 2 builds the backends in isolation but not the templates the
downstream consumer actually copies in with `nix flake init`. The
templates have their own `flake.nix` with `inputs.nixos-flake.url`,
and a regression in their composition surfaces only on an actual build.
The libvirt template's qcow2 *disk image* is also assembled here —
`make-disk-image.nix` is not exercised by step 2's libvirt closure
check.

What: builds the imageless template's `toplevel` closure and the
libvirt template's qcow2 against the local checkout, in both cases
overriding the placeholder `path:/path/to/nixos-flake` input with the
working tree.

```shell
nix build "path:./templates/imageless#packages.x86_64-linux.toplevel" \
  --override-input nixos-flake "path:$PWD"

nix build "path:./templates/libvirt#packages.x86_64-linux.image" \
  --override-input nixos-flake "path:$PWD"
```

## 4. Build the custom packages — when `pkgs/` or `overlays/` changed

Why: `nix flake check` exercises the `checks` closures but does not build
the standalone `packages` outputs; overlay and package changes only
surface on an actual build.

What: builds each custom package.

```shell
nix build .#cpupower .#damo .#libbpf-tools .#nfstest .#pynfs .#xnvme
```

## 5. Review the commit message

Why: the project enforces strict commit conventions (see CLAUDE.md).

What: subject in imperative mood, at or below 50 characters; body in
plain-English paragraphs, never bullet lists; `Generated-by:`
immediately followed by `Signed-off-by:` with no blank line between
them.
