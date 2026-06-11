# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Libvirt disk-image NixOS VM starter.
#
# Create with:
#   nix flake init --template "github:linux-kdevops/nixos-flake#libvirt"
#   nix build .#nixosConfigurations.vm.config.system.build.toplevel
#
# Per-VM configuration lives in ./default.nix. This flake composes
# the base modules, applies the overlay, and passes nixos-flake and
# the flake inputs through specialArgs so default.nix can import
# additional modules (for example nixos-flake.nixosModules.testSuites.*)
# and reference local source inputs without re-declaring them.
{
  inputs = {
    # Local checkout preferred: consumers pin to a specific
    # revision via a subtree or vendored copy and should not
    # track upstream HEAD. For upstream, use:
    #   nixos-flake.url = "github:linux-kdevops/nixos-flake";
    nixos-flake.url = "path:/path/to/nixos-flake";
    nixpkgs.follows = "nixos-flake/nixpkgs";

    # Local source checkouts (uncomment to use). Multi-attribute
    # non-flake inputs decompose into the type/path or type/url
    # attribute-set form so each piece (type, source, ref,
    # submodules) reads on its own line:
    #
    #   fio-src = {
    #     type = "path";
    #     path = "/home/user/src/fio";
    #     flake = false;
    #   };
    #   kmod-src = {
    #     type = "git";
    #     url = "https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git";
    #     ref = "master";
    #     flake = false;
    #   };
  };

  outputs =
    {
      self,
      nixpkgs,
      nixos-flake,
      ...
    }@inputs:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in
    {
      nixosConfigurations.vm = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = { inherit inputs nixos-flake; };
        modules = [
          nixos-flake.nixosModules.backends.libvirt
          nixos-flake.nixosModules.user
          { nixpkgs.overlays = [ nixos-flake.overlays.default ]; }
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
