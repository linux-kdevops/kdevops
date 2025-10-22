# install-rust-deps Role

Generic Ansible role for installing Rust toolchain dependencies across multiple
Linux distributions.

## Purpose

Provides consistent Rust build environment setup for any kdevops workflow or
role that needs Rust support. This modular role can be included via
`ansible.builtin.include_role` to ensure cargo, rustc, and pkg-config are
available.

## Packages Installed

### Debian/Ubuntu
- `cargo` - Rust package manager and build tool
- `rustc` - Rust compiler
- `pkg-config` - Helper tool for compiling applications

### Fedora/RHEL/CentOS
- `cargo` - Rust package manager and build tool
- `rust` - Rust compiler
- `pkgconfig` - Helper tool for compiling applications

### SUSE/openSUSE
- `cargo` - Rust package manager and build tool
- `rust` - Rust compiler
- `pkg-config` - Helper tool for compiling applications

## Rust Code Quality Tools

This role provides the foundation for Rust development in kdevops. After
installation, the following tools are available:

### cargo fmt
Automatic code formatter using Linux kernel rustfmt standards:
```bash
cd workflows/rcloud  # or any Rust project
cargo fmt
```

Configuration is provided via `.rustfmt.toml` in the kdevops root directory
(included with this role).

### cargo clippy
Linter for catching common mistakes and non-idiomatic code:
```bash
cd workflows/rcloud  # or any Rust project
cargo clippy --all-targets --all-features -- -D warnings
```

**Always run both tools before committing Rust code:**
1. `cargo fmt` - Auto-format according to kernel standards
2. `cargo clippy` - Fix all warnings (treated as errors with `-D warnings`)

## Usage

### Include in Your Role

```yaml
- name: Install Rust build dependencies
  ansible.builtin.include_role:
    name: install-rust-deps
```

### Example Workflows Using This Role

- **bootlinux**: Kernel builds with Rust support
- **rcloud**: Private cloud infrastructure written in Rust

## Files Provided

- `.rustfmt.toml` - Linux kernel Rust formatting configuration
  - Edition 2021
  - Unix newlines
  - Consistent code style across all kdevops Rust code

## Design Philosophy

This role follows kdevops patterns:
- Distribution-agnostic with distro-specific task files
- No conditional installation guards (always ensures packages present)
- Minimal dependencies
- Reusable across workflows

## See Also

- `install-go-deps` - Similar role for Go toolchain
- `install-rcloud-deps` - Uses this role for rcloud workflow
- `CLAUDE.md` - Code quality requirements including Rust guidelines
