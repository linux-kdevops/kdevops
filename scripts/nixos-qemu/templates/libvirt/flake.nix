# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Libvirt disk-image NixOS VM starter.
#
# Create with:
#   nix flake init --template "github:linux-kdevops/nixos-qemu#libvirt"
#   nix build .#nixosConfigurations.vm.config.system.build.toplevel
#
# Per-VM configuration lives in ./default.nix. This flake composes
# the base modules, applies the overlay, and passes nixos-qemu and
# the flake inputs through specialArgs so default.nix can import
# additional modules (for example nixos-qemu.nixosModules.workflows.*)
# and reference local source inputs without re-declaring them.
{
  inputs = {
    # Local checkout preferred: downstream consumers (kdevops and
    # others) pin to a specific revision via a subtree or vendored
    # copy, and should not track upstream HEAD. For upstream, use:
    #   nixos-qemu.url = "github:linux-kdevops/nixos-qemu";
    nixos-qemu.url = "path:/path/to/nixos-qemu";
    nixpkgs.follows = "nixos-qemu/nixpkgs";

    # Local source checkouts (uncomment to use):
    # fio-src = { url = "path:/home/user/src/fio"; flake = false; };
    # kmod-src = { url = "path:/home/user/src/kmod"; flake = false; };
  };

  outputs = { self, nixpkgs, nixos-qemu, ... }@inputs:
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
  in {
    nixosConfigurations.vm = nixpkgs.lib.nixosSystem {
      inherit system;
      specialArgs = { inherit inputs nixos-qemu; };
      modules = [
        nixos-qemu.nixosModules.libvirt
        nixos-qemu.nixosModules.user
        { nixpkgs.overlays = [ nixos-qemu.overlays.default ]; }
        ./default.nix
      ];
    };

    # qcow2 disk image built from the nixosConfiguration above.
    # Run: nix build .#image  (or .#packages.<system>.image)
    # The output is the path to the qcow2 file; libvirt consumes it
    # as <disk type='file' device='disk'>/<source file='...'/>.
    packages.${system}.image = import "${nixpkgs}/nixos/lib/make-disk-image.nix" {
      inherit pkgs;
      inherit (pkgs) lib;
      config = self.nixosConfigurations.vm.config;
      diskSize = 20480;
      format = "qcow2";
      partitionTableType = "legacy";
      installBootLoader = true;
    };
  };
}
