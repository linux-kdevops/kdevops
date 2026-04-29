# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Minimal NixOS configuration for imageless boot via virtiofs.
#
# Root is tmpfs. /nix/store and /lib/modules are mounted via virtiofs
# from the host. The kernel is built externally with all boot-critical
# drivers built-in (CONFIG_VIRTIO_FS=y, CONFIG_TMPFS=y). NixOS builds
# a systemd initramfs that mounts root (tmpfs), /nix/store, and
# /lib/modules before switch-root.
#
# Key-only SSH. Root password is serial-console break-glass only.
{ config, pkgs, lib, modulesPath, ... }: {
  imports = [ (modulesPath + "/profiles/minimal.nix") ];

  system.stateVersion = "25.11";

  services.openssh = {
    enable = true;
    settings = {
      PermitRootLogin = lib.mkDefault "yes";
      PubkeyAuthentication = true;
      PasswordAuthentication = lib.mkDefault false;
    };
  };

  # Root as tmpfs: ephemeral, no disk image. systemd in the initramfs
  # creates this from root=tmpfs on the kernel command line.
  fileSystems."/" = lib.mkImageMediaOverride {
    fsType = "tmpfs";
    options = [ "mode=0755" ];
  };

  # /nix/store via virtiofs (read-only, shared from host).
  # Automatically included in initrd fstab (pathsNeededForBoot).
  fileSystems."/nix/store" = {
    device = "store";
    fsType = "virtiofs";
  };

  # Kernel modules via virtiofs (from the external kernel build).
  # neededForBoot puts it in the initrd fstab since /lib/modules
  # is not in pathsNeededForBoot.
  fileSystems."/lib/modules" = {
    device = "modules";
    fsType = "virtiofs";
    neededForBoot = true;
  };

  # Disable systemd-remount-fs. Nothing to remount on tmpfs.
  systemd.services.systemd-remount-fs.enable = lib.mkForce false;

  # No bootloader. Kernel is external, but NixOS builds the initramfs.
  boot.loader.grub.enable = false;
  boot.kernel.enable = false;

  # Workaround: boot.kernel.enable = false does not define
  # system.build.kernel, but boot.initrd.systemd accesses
  # kernel.config.isYes and kernel.config.isSet to decide whether
  # to include kernel modules in the initramfs.
  #
  # The initrd module uses: isSet "MODULES" -> isYes "MODULES"
  # (Nix implication). To exclude modules, isSet must return true
  # and isYes must return false (true -> false = false).
  # https://github.com/NixOS/nixpkgs/issues/467069
  system.build.kernel.config = {
    isYes = _: false;
    isSet = _: true;
  };

  # systemd initramfs: systemd runs as PID 1, reads the initrd fstab,
  # mounts root + /nix/store + /lib/modules, then switch-roots.
  boot.initrd.systemd.enable = true;
  boot.initrd.supportedFilesystems = [ "virtiofs" ];

  # Passwordless emergency shell in the initramfs. Without this,
  # sulogin blocks on "root account is locked" when boot fails.
  boot.initrd.systemd.emergencyAccess = true;

  # No kernel modules in the initramfs. The external kernel has all
  # boot-critical drivers built-in (CONFIG_VIRTIO_FS=y, CONFIG_TMPFS=y,
  # CONFIG_VIRTIO_PCI=y). Runtime modules come from /lib/modules via
  # virtiofs after switch-root.
  boot.initrd.availableKernelModules = lib.mkForce [];
  boot.initrd.kernelModules = lib.mkForce [];

  # Restore the standard `boot.kernelModules → /etc/modules-load.d
  # → systemd-modules-load.service` wiring that NixOS'
  # nixos/modules/system/boot/kernel.nix gates off when
  # boot.kernel.enable=false.
  #
  # The upstream `mkIf config.boot.kernel.enable` block in
  # kernel.nix (around line 441) bundles eleven separate things
  # under one gate. Five of them genuinely depend on NixOS
  # having built the kernel itself — system.build.kernel,
  # system.modulesTree, the system.systemBuilderCommands that
  # symlink $out/kernel and $out/initrd, the kernel-side
  # boot.kernelParams, hardware.firmware exposure. Two are
  # default-module hints (loop, atkbd) that aren't useful in a
  # VM. The remaining four are pure runtime mechanism and have
  # no dependency on the kernel package whatsoever:
  #
  #   environment.etc."modules-load.d/nixos.conf"
  #   systemd.services.systemd-modules-load.wantedBy
  #   systemd.services.systemd-modules-load.serviceConfig
  #   lib.kernelConfig (assertion helpers)
  #
  # The first three are needed for `boot.kernelModules` to
  # actually load anything; the fourth is unused outside
  # NixOS-built-kernel paths. Bundling all eleven under one gate
  # was a reasonable simplification when "no kernel package =
  # no modules" was the only no-NixOS-kernel use case the
  # upstream module had to think about, but the assumption
  # breaks on imageless guests: kdevops/bootlinux builds the
  # kernel out-of-tree relative to nixpkgs, and the matching
  # modules tree lives at /lib/modules served by virtiofs from
  # the controller. The modules exist, modprobe works, the only
  # thing missing is the standard /etc/modules-load.d wiring
  # that systemd-modules-load.service consumes at stage-2 boot.
  #
  # Lifting `boot.kernel.enable = true` to use the upstream path
  # is wrong for two reasons. First, it would re-engage every
  # piece of the gate, including the system.build.kernel and
  # system.systemBuilderCommands branches that emit symlinks
  # ($out/kernel, $out/initrd) pointing at the nixpkgs kernel —
  # we'd ship two kernels (nixpkgs + bootlinux) in the closure,
  # only one of which actually runs. Second, even if we patched
  # around the symlinks, downstream tooling that reads
  # system.build.kernel (image generators, future kexec/snapshot
  # paths, debug attestation) would silently report the
  # wrong-but-built kernel rather than the actual one.
  #
  # The minimal fix is to lift only the four pure-runtime pieces
  # at this layer, where the unbundling decision happens. The
  # mkIf guard makes this a no-op if a future kernel.nix lifts
  # the gating itself, or if a downstream module ever sets
  # boot.kernel.enable=true on top of imageless (the natural
  # path for someone who wants both nixpkgs and kdevops kernels
  # available, even though that's not a path we use today). The
  # config shape and SuccessExitStatus value mirror upstream so
  # the runtime behavior is byte-identical to a kernel.enable=true
  # closure for the modules-load surface.
  environment.etc."modules-load.d/nixos.conf".source =
    lib.mkIf (!config.boot.kernel.enable) (pkgs.writeText "nixos.conf" ''
      ${lib.concatStringsSep "\n" config.boot.kernelModules}
    '');
  systemd.services.systemd-modules-load = lib.mkIf (!config.boot.kernel.enable) {
    wantedBy = [ "multi-user.target" ];
    serviceConfig.SuccessExitStatus = "0 1";
  };

  # Serial getty on hvc0 for interactive login via the console socket.
  # hvc0 is a virtio console, handled by systemd's serial-getty@ template
  # (the plain getty@ template is VT-only, gated on /dev/tty0).
  # Requires CONFIG_VIRTIO_CONSOLE=y (or =m) in the guest kernel.
  systemd.services."serial-getty@hvc0" = {
    enable = true;
    wantedBy = [ "getty.target" ];
  };

  # Serial-console break-glass. Tmpfs root resets it every boot.
  users.mutableUsers = false;
  users.users.root.initialPassword = "root";

  # Networking: systemd-networkd with DHCP on all ethernet interfaces.
  networking.useNetworkd = true;
  networking.hostName = lib.mkDefault "nixos";
  networking.firewall.enable = false;
  systemd.network.networks."80-ethernet" = {
    matchConfig.Name = "en*";
    networkConfig.DHCP = "yes";
  };

  # Disable unnecessary services.
  systemd.oomd.enable = false;
  nix.enable = false;
  services.lvm.enable = false;

  environment.systemPackages = with pkgs; [ coreutils ];
}
