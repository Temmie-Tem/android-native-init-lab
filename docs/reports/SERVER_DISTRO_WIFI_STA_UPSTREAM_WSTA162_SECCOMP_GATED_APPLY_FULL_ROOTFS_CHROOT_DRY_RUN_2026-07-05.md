# WSTA162 Seccomp Gated-Apply Full-Rootfs Chroot Dry-Run Pass

Date: 2026-07-05 13:12 KST

## Verdict

WSTA162 stages the WSTA161 gated-apply helper into a private full rootfs copy
and re-runs the full-rootfs chroot dry-run.  The default in-rootfs helper path
is unchanged:

```text
/usr/lib/a90-dpublic/seccomp/a90-seccomp-loader-checkonly
```

but it now points to the WSTA161 apply-capable helper.  The launcher still
invokes the helper in check-only mode and still blocks actual seccomp
load/enforcement.  This unit is host-only: it did not touch the device, flash,
reboot, connect Wi-Fi, run DHCP, open a public tunnel, mutate packet filters,
write userdata, load BPF, load a seccomp filter, or enforce seccomp.

Result: PASS.  Inside `unshare -r chroot`, the default helper path emitted
WSTA161 markers, proved `A90WSTA161_SECCOMP_LOAD=0`, did not emit a load-attempt
marker, and the launcher exited `65` before exec with
`blocked-seccomp-enforce-unimplemented`.

## Source Changes

- Updated
  `workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py`:
  - accepts both WSTA158 check-only helper manifests and WSTA161 gated-apply
    helper manifests in `stage_seccomp_loader_helper`.
  - validates WSTA161 shape: gated-apply schema, compiled apply code,
    default load disabled, `loaded=false`, and `enforced=false`.
  - records `helper_schema` and `apply_code_compiled` in staging metadata.
- Added
  `workspace/public/src/scripts/server-distro/run_wsta162_seccomp_gated_apply_full_rootfs_chroot_dry_run.py`.
- Added focused tests in
  `tests/test_server_distro_wsta162_seccomp_gated_apply_full_rootfs_chroot_dry_run.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta162-seccomp-gated-apply-full-rootfs-chroot-dry-run-20260705T1312KST/
```

Inputs:

```text
workspace/private/builds/server-distro/d3-sysvinit-usrmerge-wsta-20260704T0225Z-rootfs
workspace/private/runs/server-distro/wsta153-seccomp-policy-source-20260705T1207KST/wsta153_seccomp_policy.json
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filter_manifest.json
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filters.o
workspace/private/runs/server-distro/wsta161-seccomp-loader-gated-apply-helper-20260705T1307KST/wsta161_seccomp_loader_helper_manifest.json
workspace/private/runs/server-distro/wsta161-seccomp-loader-gated-apply-helper-20260705T1307KST/a90-seccomp-loader-gated-apply
```

Decision:

```text
wsta162-seccomp-gated-apply-full-rootfs-chroot-dry-run-pass
```

Default dry-run stdout:

```text
A90WSTA154_SECCOMP_POLICY_PRESENT=1
A90WSTA154_SECCOMP_DRY_RUN_ONLY=1
A90WSTA154_SECCOMP_FILTER_LOAD=0
A90WSTA154_SECCOMP_SERVICE=dpublic-hud
A90WSTA154_SECCOMP_POLICY_SERVICE=dpublic-hud-intent
A90WSTA154_SECCOMP_PROFILE=seccomp-dpublic-hud-intent-observed-v1
A90WSTA154_SECCOMP_ALLOWLIST_COUNT=22
A90WSTA157_SECCOMP_ARTIFACT_PRESENT=1
A90WSTA157_SECCOMP_ENFORCE_FLAG=0
A90WSTA159_SECCOMP_HELPER_PRESENT=1
A90WSTA159_SECCOMP_HELPER_CHECK_ONLY=1
a90_service_launcher_decision=exec
fake_setpriv_args=--no-new-privs --reuid a90hud --regid a90hud --init-groups -- /bin/true
```

Enforce-flag chroot stdout:

```text
A90WSTA157_SECCOMP_ENFORCE_FLAG=1
A90WSTA159_SECCOMP_HELPER_PRESENT=1
A90WSTA159_SECCOMP_HELPER_CHECK_ONLY=1
A90WSTA161_LOADER_GATED_APPLY=1
A90WSTA161_SECCOMP_LOAD=0
A90WSTA161_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49
a90_seccomp_loader_decision=check-only
A90WSTA159_SECCOMP_HELPER_CHECK_ONLY_OK=1
a90_service_launcher_decision=blocked-seccomp-enforce-unimplemented
```

## Checks

WSTA162 fail-closes unless:

- the proof is explicitly gated.
- source rootfs and all WSTA153/WSTA156/WSTA161 inputs are private.
- WSTA156 object SHA matches its manifest.
- WSTA161 helper SHA matches its manifest.
- WSTA161 helper manifest says apply code is compiled, default load is
  disabled, `loaded=false`, and `enforced=false`.
- the helper is staged at the default chroot path.
- dry-run with enforcement off reaches fake `setpriv`.
- enforce flag runs the default-path WSTA161 helper in check-only mode.
- helper output proves `A90WSTA161_SECCOMP_LOAD=0`.
- helper output does not include `A90WSTA161_SECCOMP_LOAD_ATTEMPT=1`.
- the launcher exits `65` before exec with
  `blocked-seccomp-enforce-unimplemented`.

## Validation

- `py_compile`:
  - `prepare_wsta3_sta_rootfs.py`
  - `run_wsta162_seccomp_gated_apply_full_rootfs_chroot_dry_run.py`
  - `test_server_distro_wsta162_seccomp_gated_apply_full_rootfs_chroot_dry_run.py`
- Focused prepare-rootfs + WSTA161 + WSTA162 tests: `41 tests OK`.
- Full server-distro regression: `558 tests OK`.
- WSTA162 proof generation from the real full source rootfs and real
  WSTA153/WSTA156/WSTA161 artifacts: pass.

## Next

WSTA163 should add an explicit live-gate design for observing the staged
gated-apply helper on device without enabling the real load token, or continue
host-only hardening by wiring a future `--apply` path that remains token-gated.
Actual enforcement remains unproven and must stay behind an explicit later
gate.
