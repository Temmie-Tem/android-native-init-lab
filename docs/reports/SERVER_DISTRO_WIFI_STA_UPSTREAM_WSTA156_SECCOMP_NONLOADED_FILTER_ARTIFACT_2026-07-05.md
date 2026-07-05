# WSTA156 Seccomp Non-Loaded Filter Artifact Pass

Date: 2026-07-05 12:27 KST

## Verdict

WSTA156 builds a non-loaded seccomp filter artifact from the WSTA153 source
policy.  This unit is host-only: it did not chroot, touch the device, flash,
reboot, connect Wi-Fi, run DHCP, open a public tunnel, mutate packet filters,
write userdata, load BPF, load a seccomp filter, or enforce seccomp.

Result: PASS.  Every WSTA153 syscall name resolved against the host aarch64
syscall table, classic-BPF `struct sock_filter` arrays were emitted as C, and
the source compiled to an aarch64 relocatable object.  The artifact records
`loaded=false` and `enforced=false`.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta156_seccomp_nonloaded_filter_artifact.py`.
- Added focused tests in
  `tests/test_server_distro_wsta156_seccomp_nonloaded_filter_artifact.py`.

## Generated Artifact

Artifact run:

```text
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/
```

Input WSTA153 policy:

```text
workspace/private/runs/server-distro/wsta153-seccomp-policy-source-20260705T1207KST/wsta153_seccomp_policy.json
```

Decision:

```text
wsta156-seccomp-nonloaded-filter-artifact-pass
```

Generated files:

```text
wsta156_seccomp_filter_manifest.json
wsta156_seccomp_filters.c
wsta156_seccomp_filters.o
```

Object identity:

```text
ELF 64-bit LSB relocatable, ARM aarch64, version 1 (SYSV), not stripped
```

SHA256:

| Artifact | SHA256 |
| --- | --- |
| C source | `bb35ee4004bc2170a638e13ee4740ef0ab13c40c5e92394ae356ea2e3dfef583` |
| Object | `41e7cf7e6f39cf2c8fa4dc974f3456bfbe7d3959a5a2c8e85628b72c4d5ae854` |

Service filters:

| Service | Resolved syscalls | BPF instruction count |
| --- | ---: | ---: |
| `dpublic-smoke-httpd` | 18 | 39 |
| `cloudflared-quick-tunnel` | 52 | 107 |
| `dropbear-admin-usb` | 53 | 109 |
| `dpublic-hud-intent` | 22 | 47 |

Unique syscall names across all services: `82`.

## Checks

WSTA156 fail-closes unless:

- the artifact build is explicitly gated.
- run directory and WSTA153 input policy are private.
- `aarch64-linux-gnu-gcc` is present.
- WSTA153 schema/state/enforcement state are exact.
- every WSTA153 profile is default-deny, non-empty, and not enforced.
- native uplink and native HUD presenter remain excluded.
- every syscall name resolves to an aarch64 syscall number.
- the emitted C compiles with `-Wall -Wextra -Werror`.
- the object is an aarch64 relocatable ELF.
- manifest states `SECCOMP_FILTER_ARTIFACT_COMPILED_NOT_LOADED`,
  `loaded=false`, and `enforced=false`.

## Validation

- `py_compile`:
  - `run_wsta156_seccomp_nonloaded_filter_artifact.py`
  - `test_server_distro_wsta156_seccomp_nonloaded_filter_artifact.py`
- Focused WSTA154 + WSTA155 + WSTA156 tests: `9 tests OK`.
- Full server-distro regression: `544 tests OK`.
- WSTA156 artifact generation from the real WSTA153 policy: pass.

## Next

WSTA157 should add a loader contract without enabling it by default: wire the
compiled artifact into the launcher model behind an explicit future enforcement
flag, or run a private chroot dry-run using the staged policy and compiled
artifact.  Enforcement remains unproven and must stay behind a separate live
gate.
