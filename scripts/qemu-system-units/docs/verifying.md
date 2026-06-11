# Verifying changes

Run these steps before every commit. They are manual for now; whether
and how to wire them as git hooks is a later decision. Each step states
why it exists and what it does.

## 1. Render the templates — `minijinja-cli --trim-blocks`

Why: a template that fails to render, or renders a malformed unit, is a
bug. Rendering is the only way to see what systemd actually consumes.

What: render every template you changed against a vars file (see the
rendering invocation in CLAUDE.md and the README quick start). A
non-zero exit or a Jinja error means the template is broken;
`virtiofsd.env.j2` and the per-VM override templates also need their
`--define` arguments.

## 2. Verify the unit files — `systemd-analyze verify`

Why: catches unknown directives and sections (which systemd silently
ignores at runtime), unresolvable `Documentation=` man pages,
`ExecStart=` binaries that are not found, and socket-to-service name
mismatches.

What: run `systemd-analyze verify` on the rendered `.service` and
`.socket` units. For the `@`-template units it substitutes a test
instance. A clean run prints nothing.

```shell
systemd-analyze verify <rendered>/qemu-system@.service
systemd-analyze verify <rendered>/virtiofsd@.socket <rendered>/virtiofsd@.service
```

## 3. Review the security posture — `systemd-analyze security`

Why: the service units ship unhardened by design (see
design-decisions.md "Security hardening"), so they score UNSAFE. This
step is to confirm a change has not *regressed* the posture or removed
a directive an operator's override depends on — not to chase a perfect
score.

```shell
systemd-analyze security <rendered>/qemu-system@.service
```

## 4. Syntax-check the shell template

Why: `transient-run.sh.j2` renders an executable script; a Jinja change
can produce a syntactically broken shell script that renders fine but
fails at `bash`.

What: `bash -n <rendered>/transient-run.sh` after rendering it.

## 5. Review the commit message

Why: the project enforces strict commit conventions (see CLAUDE.md).

What: subject in imperative mood; body in plain-English paragraphs,
never bullet lists; `Generated-by:` immediately followed by
`Signed-off-by:` with no blank line between them.
