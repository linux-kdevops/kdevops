{
  description = "kdevops NixOS VMs";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }: {
    nixosConfigurations = {
      "kdevops" = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          ./generated/configuration.nix
          ./generated/hardware-configuration.nix
          ./generated/workflow-deps.nix
          ({ ... }: {
            networking.hostName = "kdevops";
          })
        ];
      };
    };

    # Build all VMs
    defaultPackage.x86_64-linux =
      nixpkgs.legacyPackages.x86_64-linux.writeShellScriptBin "build-vms" ''
        echo "Building NixOS VMs..."
        echo "Building kdevops..."
        nix build .#nixosConfigurations.kdevops.config.system.build.vm
        echo "All VMs built successfully!"
      '';
  };
}
