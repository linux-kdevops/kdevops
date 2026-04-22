# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Library flake: NixOS modules (imageless, libvirt, user, devel),
# overlays, templates, and custom packages for QEMU VMs.
#
# Validate both backends:
#   nix flake check
#
# Build a single backend closure:
#   nix build .#checks.x86_64-linux.imageless
#   nix build .#checks.x86_64-linux.libvirt
#
# Build an individual custom package:
#   nix build .#cpupower
#
# Create a downstream configuration:
#   nix flake init --template "github:linux-kdevops/nixos-qemu"
#   nix flake init --template "github:linux-kdevops/nixos-qemu#libvirt"
{
  description = "NixOS modules and overlays for QEMU VMs";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

  outputs = { self, nixpkgs }:
  let
    systems = [ "x86_64-linux" "aarch64-linux" ];
    forAllSystems = f: nixpkgs.lib.genAttrs systems (system:
      f (import nixpkgs {
        inherit system;
        overlays = [ self.overlays.default ];
      }));
  in {
    nixosModules = {
      build-tools = ./modules/build-tools.nix;
      devel = ./modules/devel.nix;
      imageless = ./modules/imageless.nix;
      libvirt = ./modules/libvirt.nix;
      shares = ./modules/shares.nix;
      storage = ./modules/storage.nix;
      user = ./modules/user.nix;
      workflows.blktests = ./modules/workflows/blktests.nix;
      workflows.fstests = ./modules/workflows/fstests.nix;
      workflows.gitr = ./modules/workflows/gitr.nix;
      workflows.ltp = ./modules/workflows/ltp.nix;
      workflows.mmtests = ./modules/workflows/mmtests.nix;
      workflows.pynfs = ./modules/workflows/pynfs.nix;
      workflows.selftests = ./modules/workflows/selftests.nix;
      workflows.sysbench = ./modules/workflows/sysbench.nix;
    };

    overlays.default = import ./overlays;

    templates = {
      default = self.templates.imageless;
      imageless = {
        path = ./templates/imageless;
        description = "Imageless NixOS VM (tmpfs root, virtiofs /nix/store, external kernel)";
      };
      libvirt = {
        path = ./templates/libvirt;
        description = "Libvirt-managed disk-image NixOS VM";
      };
    };

    # Expose the custom packages as direct flake outputs so they can be
    # built without going through a NixOS configuration.
    packages = forAllSystems (pkgs: {
      inherit (pkgs) cpupower damo libbpf-tools nfstest pynfs xnvme;
    });

    # Per-backend system closures exercised by nix flake check.
    checks = nixpkgs.lib.genAttrs systems (system:
      let
        buildBackend = module: (nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [
            module
            { nixpkgs.overlays = [ self.overlays.default ]; }
          ];
        }).config.system.build.toplevel;
      in {
        imageless = buildBackend self.nixosModules.imageless;
        libvirt = buildBackend self.nixosModules.libvirt;
      });
  };
}
