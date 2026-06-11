# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Library flake: NixOS modules, overlays, templates, and custom
# packages for provisioning NixOS systems. Two backend modules
# differ in the artifact each produces — imageless yields a system
# closure booted directly by QEMU, libvirt yields a qcow2 disk
# image.
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
#   nix flake init --template "github:linux-kdevops/nixos-flake"
#   nix flake init --template "github:linux-kdevops/nixos-flake#libvirt"
{
  description = "NixOS modules, overlays, and templates for provisioning NixOS systems";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems =
        f:
        nixpkgs.lib.genAttrs systems (
          system:
          f (
            import nixpkgs {
              inherit system;
              overlays = [ self.overlays.default ];
            }
          )
        );
    in
    {
      # The on-disk layout groups modules into nix-native buckets:
      #
      #   backends/   complete system shape (imageless, libvirt) —
      #               import one and only one per nixosSystem
      #   profiles/   additive feature sets (build-tools, controller,
      #               devel, monitoring) on top of a backend
      #   mounts/     fileSystems-emitting DSLs (shares, storage)
      #   testSuites/ per-suite modules (fstests, blktests, …)
      #
      # The nixosModules attrset mirrors this layout so the import
      # path matches the file path.
      nixosModules = {
        # The default aggregate matches the imageless template's
        # starter composition (imageless backend plus the opt-in
        # unprivileged account). Consumers that prefer the libvirt
        # backend or want bare modules import them by name.
        default.imports = [
          ./modules/backends/imageless
          ./modules/user.nix
        ];

        backends = {
          imageless = ./modules/backends/imageless;
          libvirt = ./modules/backends/libvirt;
        };

        profiles = {
          build-tools = ./modules/profiles/build-tools.nix;
          controller = ./modules/profiles/controller.nix;
          devel = ./modules/profiles/devel.nix;
          monitoring = ./modules/profiles/monitoring.nix;
        };

        mounts = {
          shares = ./modules/mounts/shares.nix;
          storage = ./modules/mounts/storage.nix;
        };

        testSuites = {
          blktests = ./modules/testSuites/blktests.nix;
          fstests = ./modules/testSuites/fstests.nix;
          gitr = ./modules/testSuites/gitr.nix;
          ltp = ./modules/testSuites/ltp.nix;
          mmtests = ./modules/testSuites/mmtests.nix;
          pynfs = ./modules/testSuites/pynfs.nix;
          selftests = ./modules/testSuites/selftests.nix;
          sysbench = ./modules/testSuites/sysbench.nix;
        };

        user = ./modules/user.nix;
      };

      overlays = {
        default = import ./overlays;
        fio = import ./overlays/fio.nix;
        xfstests = import ./overlays/xfstests.nix;
        custom-pkgs = final: _: import ./pkgs final;
      };

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
        inherit (pkgs)
          cpupower
          damo
          libbpf-tools
          nfstest
          pynfs
          xnvme
          ;
      });

      # Tree formatter for `nix fmt`. No overlay needed, so this uses
      # legacyPackages rather than re-importing nixpkgs.
      formatter = nixpkgs.lib.genAttrs systems (
        system: nixpkgs.legacyPackages.${system}.nixfmt-rfc-style
      );

      # Per-backend system closures exercised by nix flake check.
      checks = nixpkgs.lib.genAttrs systems (
        system:
        let
          buildBackend =
            module:
            (nixpkgs.lib.nixosSystem {
              inherit system;
              modules = [
                module
                { nixpkgs.overlays = [ self.overlays.default ]; }
              ];
            }).config.system.build.toplevel;

          # Build each test-suite module composed on top of the
          # imageless backend plus the unprivileged account and
          # the monitoring profile. The composition is the
          # realistic shape a consumer deploys (a guest that runs
          # a test suite on an unprivileged account with monitor
          # units available), so a test-suite module that conflicts
          # with imageless, user, or monitoring defaults surfaces
          # in nix flake check rather than at consumer bringup.
          # Monitoring is composed alongside because the monitor
          # template units (monitor-<name>@<run-id>.service)
          # exercise systemd template-instantiation paths that
          # standalone evaluation of the module does not.
          testSuiteChecks = nixpkgs.lib.mapAttrs' (
            name: module:
            nixpkgs.lib.nameValuePair "imageless-${name}" (buildBackend {
              imports = [
                self.nixosModules.backends.imageless
                self.nixosModules.user
                self.nixosModules.profiles.monitoring
                module
              ];
              nixos-flake.monitoring.enable = true;
            })
          ) self.nixosModules.testSuites;
        in
        {
          imageless = buildBackend self.nixosModules.backends.imageless;
          libvirt = buildBackend self.nixosModules.backends.libvirt;
          # The controller profile composes on top of a disk-booted
          # backend; build it against libvirt so the check exercises
          # the realistic control-node configuration.
          controller = buildBackend {
            imports = [
              self.nixosModules.backends.libvirt
              self.nixosModules.profiles.controller
            ];
            nixos-flake.controller.enable = true;
          };
        }
        // testSuiteChecks
      );
    };
}
