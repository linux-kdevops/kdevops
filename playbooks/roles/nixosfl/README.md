# playbooks/roles/nixos_flake -- nixos_flake role

Thin role wrapping the vendored nixos-flake Nix library at
`scripts/nixos-flake/`. Per-VM glue templates the role renders
reference the flake via:

```nix
inputs.nixos-flake.url = "path:{{ nixos_flake_path }}";
```

so updating the subtree via `git subtree pull --squash` immediately
reaches every generated per-VM flake.
