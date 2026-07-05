# WSTA158 Seccomp Loader Check-Only Helper Pass

Date: 2026-07-05 12:43 KST

## Verdict

WSTA158 builds a separate aarch64 seccomp-loader helper linked against the
WSTA156 non-loaded filter object, then proves the helper's default mode is
check-only under `qemu-aarch64`.  This unit is host-only: it did not chroot,
touch the device, flash, reboot, connect Wi-Fi, run DHCP, open a public tunnel,
mutate packet filters, write userdata, load BPF, load a seccomp filter, or
enforce seccomp.

Result: PASS.  The helper links all four WSTA156 service filters, enumerates
their lengths in check-only mode, maps launcher service `dpublic-hud` to policy
service `dpublic-hud-intent`, and fail-closes `--apply` before any load path
with `blocked-allow-load-required`.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta158_seccomp_loader_checkonly_helper.py`.
  - consumes the WSTA156 manifest/object from private paths.
  - validates the WSTA156 object SHA against the manifest.
  - emits a small C helper with WSTA156 symbol declarations.
  - compiles a static ARM64 helper with `aarch64-linux-gnu-gcc`.
  - runs the helper through `qemu-aarch64` in default check-only,
    service-specific check-only, and blocked apply modes.
  - keeps actual seccomp/BPF loading absent from this unit.
- Added focused tests in
  `tests/test_server_distro_wsta158_seccomp_loader_checkonly_helper.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta158-seccomp-loader-checkonly-helper-20260705T1243KST/
```

Inputs:

```text
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filter_manifest.json
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filters.o
```

Decision:

```text
wsta158-seccomp-loader-checkonly-helper-pass
```

Helper artifact:

```text
workspace/private/runs/server-distro/wsta158-seccomp-loader-checkonly-helper-20260705T1243KST/a90-seccomp-loader-checkonly
SHA256: 4883eae48e85cc504b1534141a64cea15681d0c5c9cf703f5fc9814f2b1900a0
file: ELF 64-bit LSB executable, ARM aarch64, statically linked
```

Default check-only stdout:

```text
A90WSTA158_LOADER_CHECK_ONLY=1
A90WSTA158_SECCOMP_LOAD=0
A90WSTA158_LINKED_SERVICE_COUNT=4
A90WSTA158_AUDIT_ARCH_AARCH64=3221225655
A90WSTA158_PROFILE service=dpublic-smoke-httpd policy_service=dpublic-smoke-httpd profile=seccomp-dpublic-smoke-httpd-observed-v1 len=41
A90WSTA158_PROFILE service=cloudflared-quick-tunnel policy_service=cloudflared-quick-tunnel profile=seccomp-cloudflared-quick-tunnel-observed-v1 len=109
A90WSTA158_PROFILE service=dropbear-admin-usb policy_service=dropbear-admin-usb profile=seccomp-dropbear-admin-usb-observed-v1 len=111
A90WSTA158_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49
a90_seccomp_loader_decision=check-only
```

Service-specific check-only stdout:

```text
A90WSTA158_LOADER_CHECK_ONLY=1
A90WSTA158_SECCOMP_LOAD=0
A90WSTA158_LINKED_SERVICE_COUNT=4
A90WSTA158_AUDIT_ARCH_AARCH64=3221225655
A90WSTA158_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49
a90_seccomp_loader_decision=check-only
```

Apply negative proof:

```text
A90WSTA158_LOADER_CHECK_ONLY=1
A90WSTA158_SECCOMP_LOAD=0
A90WSTA158_LINKED_SERVICE_COUNT=4
A90WSTA158_AUDIT_ARCH_AARCH64=3221225655
a90_seccomp_loader_decision=blocked-allow-load-required
```

## Checks

WSTA158 fail-closes unless:

- the proof is explicitly gated.
- run directory, WSTA156 manifest, and WSTA156 object are private.
- WSTA156 manifest says `SECCOMP_FILTER_ARTIFACT_COMPILED_NOT_LOADED`,
  `loaded=false`, and `enforced=false`.
- WSTA156 object SHA matches the manifest.
- the manifest contains exactly the four expected policy services.
- `aarch64-linux-gnu-gcc` and `qemu-aarch64` are present.
- the helper builds as a static ARM64 executable.
- qemu default check-only prints all four linked profiles.
- qemu service check maps `dpublic-hud` to `dpublic-hud-intent`.
- qemu `--apply` returns `65` with `A90WSTA158_SECCOMP_LOAD=0` and
  `blocked-allow-load-required`.

## Validation

- `py_compile`:
  - `run_wsta158_seccomp_loader_checkonly_helper.py`
  - `test_server_distro_wsta158_seccomp_loader_checkonly_helper.py`
- Focused WSTA156 + WSTA157 + WSTA158 tests: `8 tests OK`.
- Full server-distro regression: `549 tests OK`.
- WSTA158 proof generation from the real WSTA156 artifact: pass.

## Next

WSTA159 should stage the check-only helper into the private rootfs and wire the
launcher enforcement flag to call the helper in check-only mode first, while
still blocking any actual load/enforcement path.  Actual seccomp enforcement
remains unproven and must stay behind a later explicit live gate.
