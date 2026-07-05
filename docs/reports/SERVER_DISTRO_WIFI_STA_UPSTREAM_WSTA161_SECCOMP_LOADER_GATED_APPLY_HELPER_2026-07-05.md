# WSTA161 Seccomp Loader Gated Apply Helper Pass

Date: 2026-07-05 13:07 KST

## Verdict

WSTA161 builds a separate ARM64 seccomp-loader helper that contains real
`prctl(PR_SET_NO_NEW_PRIVS)` and `prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER,
...)` apply code, but keeps default behavior and all proof executions
non-loading.  `--apply` fails closed unless both `A90WSTA161_ALLOW_LOAD=1` and
a later explicit token are supplied.  This unit never supplies the correct
token, so it does not chroot, touch the device, flash, reboot, connect Wi-Fi,
run DHCP, open a public tunnel, mutate packet filters, write userdata, load
BPF, load a seccomp filter, or enforce seccomp.

Result: PASS.  The helper links the real WSTA156 filter object, compiles the
target apply function into the ARM64 binary, proves the load symbol is present,
and proves both missing-gate and wrong-token apply runs stop before any load
attempt marker.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta161_seccomp_loader_gated_apply_helper.py`.
  - consumes the WSTA156 manifest/object from private paths.
  - emits an ARM64 C helper with a real `a90_wsta161_load_profile()` function.
  - compiles the helper as a static ARM64 binary.
  - verifies source contains `PR_SET_NO_NEW_PRIVS`, `PR_SET_SECCOMP`,
    `A90WSTA161_ALLOW_LOAD`, and `A90WSTA161_LOAD_TOKEN`.
  - verifies the binary contains `a90_wsta161_load_profile` via
    `aarch64-linux-gnu-nm`.
  - runs qemu check-only, service check-only, missing-gate apply block, and
    wrong-token apply block.
- Added focused tests in
  `tests/test_server_distro_wsta161_seccomp_loader_gated_apply_helper.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta161-seccomp-loader-gated-apply-helper-20260705T1307KST/
```

Inputs:

```text
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filter_manifest.json
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filters.o
```

Decision:

```text
wsta161-seccomp-loader-gated-apply-helper-pass
```

Helper artifact:

```text
workspace/private/runs/server-distro/wsta161-seccomp-loader-gated-apply-helper-20260705T1307KST/a90-seccomp-loader-gated-apply
SHA256: daec5202255b5b95871152fd8f747c7ca60b277d359f81a6d03e54189c028992
file: ELF 64-bit LSB executable, ARM aarch64, statically linked
```

Static source/symbol proof:

```text
PR_SET_NO_NEW_PRIVS present
PR_SET_SECCOMP present
A90WSTA161_ALLOW_LOAD present
A90WSTA161_LOAD_TOKEN present
0000000000400a14 T a90_wsta161_load_profile
```

Service check-only stdout:

```text
A90WSTA161_LOADER_GATED_APPLY=1
A90WSTA161_SECCOMP_LOAD=0
A90WSTA161_LINKED_SERVICE_COUNT=4
A90WSTA161_AUDIT_ARCH_AARCH64=3221225655
A90WSTA161_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49
a90_seccomp_loader_decision=check-only
```

Missing-gate apply stdout:

```text
A90WSTA161_LOADER_GATED_APPLY=1
A90WSTA161_SECCOMP_LOAD=0
A90WSTA161_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49
a90_seccomp_loader_decision=blocked-load-gate-required
```

Wrong-token apply stdout:

```text
A90WSTA161_LOADER_GATED_APPLY=1
A90WSTA161_SECCOMP_LOAD=0
A90WSTA161_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49
a90_seccomp_loader_decision=blocked-load-token-required
```

## Checks

WSTA161 fail-closes unless:

- the proof is explicitly gated.
- run directory, WSTA156 manifest, and WSTA156 object are private.
- WSTA156 object SHA matches its manifest.
- `aarch64-linux-gnu-gcc`, `qemu-aarch64`, and `aarch64-linux-gnu-nm` are
  present.
- source includes the no-new-privs/seccomp apply calls and env-token gates.
- the helper builds as static ARM64.
- `a90_wsta161_load_profile` is present in the binary symbol table.
- check-only runs print all linked services.
- `--apply` without env returns `65` with `blocked-load-gate-required`.
- `--apply` with wrong token returns `65` with `blocked-load-token-required`.
- neither apply-block run prints `A90WSTA161_SECCOMP_LOAD_ATTEMPT=1`.

## Validation

- `py_compile`:
  - `run_wsta161_seccomp_loader_gated_apply_helper.py`
  - `test_server_distro_wsta161_seccomp_loader_gated_apply_helper.py`
- Focused WSTA158 + WSTA159 + WSTA160 + WSTA161 tests: `10 tests OK`.
- Full server-distro regression: `556 tests OK`.
- WSTA161 proof generation from the real WSTA156 artifact: pass.

## Next

WSTA162 should stage the WSTA161 gated-apply helper into the private rootfs and
run the full-rootfs chroot dry-run again, proving the default in-rootfs helper
path now uses the apply-capable helper while still blocking actual load and
enforcement.
