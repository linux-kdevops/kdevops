# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Library flake for provisioning NixOS systems: backend modules (imageless
# closure / libvirt disk image), profiles, overlays, packages and templates,
# plus build-kernel/build-qemu/systemd devShells that bring the same toolchain
# (lib/toolchain.nix) to any host via `nix develop`.
#
#   nix flake check                             # validate backends + checks
#   nix build .#checks.x86_64-linux.imageless   # one backend closure
#   nix develop .#build-kernel -c make ...      # kernel build env
#   nix flake init -t github:linux-kdevops/nixos-flake
{
  description = "NixOS modules, overlays, and templates for provisioning NixOS systems";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

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
          qemu
          virtiofsd
          socat
          ;
      });

      # Reproducible build toolchains usable on any host (NixOS or not). Nix
      # provides the environment; the build picks the compiler/flags inside it.
      #   nix develop .#build-kernel -c make ...
      #   nix develop .#build-qemu   -c make ...
      devShells = forAllSystems (
        pkgs:
        let
          tc = import ./lib/toolchain.nix { inherit pkgs; };
          kernelPackages =
            tc.kernel
            ++ tc.matrixExtras
            ++ [
              pkgs.ccache
              pkgs.b4
            ];
          # CONFIG_RUST builds core/alloc from source -> needs rust-src.
          rustLibSrc = pkgs.rustPlatform.rustLibSrc;
        in
        {
          # No qemu inputsFrom: its NIX_CFLAGS_COMPILE overflows the kernel
          # host-tool argv (E2BIG on fixdep).
          build-kernel = pkgs.mkShell {
            packages = kernelPackages;
            env.RUST_LIB_SRC = rustLibSrc;
          };

          # Adds qemu's build inputs via inputsFrom + the python deps qemu's
          # offline configure venv (mkvenv) needs.
          build-qemu = pkgs.mkShell {
            inputsFrom = [ pkgs.qemu ];
            packages = kernelPackages ++ [
              (pkgs.python3.withPackages (
                ps: with ps; [
                  setuptools
                  wheel
                  pip
                ]
              ))
            ];
            env.RUST_LIB_SRC = rustLibSrc;
          };

          # systemd client tools to drive a host user manager over D-Bus.
          systemd = pkgs.mkShell {
            packages = [ pkgs.systemd ];
          };
        }
      );

      # Tree formatter for `nix fmt`. No overlay needed, so this uses
      # legacyPackages rather than re-importing nixpkgs.
      formatter = nixpkgs.lib.genAttrs systems (system: nixpkgs.legacyPackages.${system}.nixfmt);

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
          devel = buildBackend {
            imports = [
              self.nixosModules.backends.imageless
              self.nixosModules.profiles.devel
            ];
          };
        }
        // testSuiteChecks
      );
    };
}
