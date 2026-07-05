# WSTA160 Seccomp Full-Rootfs Chroot Dry-Run Pass

Date: 2026-07-05 13:00 KST

## Verdict

WSTA160 proves the WSTA159 seccomp launcher path inside a private full rootfs
copy, using `unshare -r chroot` and the default in-rootfs helper path:
`/usr/lib/a90-dpublic/seccomp/a90-seccomp-loader-checkonly`.  This unit is
host-only: it did not touch the device, flash, reboot, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, load BPF, load a
seccomp filter, or enforce seccomp.

Result: PASS.  The staged ARM64 helper executed through host binfmt from its
default chroot path, printed `A90WSTA158_SECCOMP_LOAD=0`, and the launcher then
blocked actual enforcement with `blocked-seccomp-enforce-unimplemented`.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta160_seccomp_full_rootfs_chroot_dry_run.py`.
  - copies the private source rootfs to a private run directory.
  - stages service identities, launcher, hardening policy, WSTA153 policy,
    WSTA156 filter artifact, and WSTA158 helper.
  - enters the private rootfs with `unshare -r chroot`.
  - uses `/fakebin/setpriv` only to observe the exec boundary.
  - leaves seccomp/BPF loading absent and blocked.
- Added focused tests in
  `tests/test_server_distro_wsta160_seccomp_full_rootfs_chroot_dry_run.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta160-seccomp-full-rootfs-chroot-dry-run-20260705T1300KST/
```

Inputs:

```text
workspace/private/builds/server-distro/d3-sysvinit-usrmerge-wsta-20260704T0225Z-rootfs
workspace/private/runs/server-distro/wsta153-seccomp-policy-source-20260705T1207KST/wsta153_seccomp_policy.json
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filter_manifest.json
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filters.o
workspace/private/runs/server-distro/wsta158-seccomp-loader-checkonly-helper-20260705T1243KST/wsta158_seccomp_loader_helper_manifest.json
workspace/private/runs/server-distro/wsta158-seccomp-loader-checkonly-helper-20260705T1243KST/a90-seccomp-loader-checkonly
```

Decision:

```text
wsta160-seccomp-full-rootfs-chroot-dry-run-pass
```

Default helper path inside chroot:

```text
/usr/lib/a90-dpublic/seccomp/a90-seccomp-loader-checkonly
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
A90WSTA158_LOADER_CHECK_ONLY=1
A90WSTA158_SECCOMP_LOAD=0
A90WSTA158_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49
a90_seccomp_loader_decision=check-only
A90WSTA159_SECCOMP_HELPER_CHECK_ONLY_OK=1
a90_service_launcher_decision=blocked-seccomp-enforce-unimplemented
```

## Checks

WSTA160 fail-closes unless:

- the proof is explicitly gated.
- source rootfs and all WSTA153/WSTA156/WSTA158 inputs are private.
- `unshare` is present.
- the full rootfs copy succeeds.
- the helper is staged at the default chroot path.
- dry-run with enforcement off reaches fake `setpriv`.
- enforce flag runs the default-path helper inside chroot.
- helper output proves `A90WSTA158_SECCOMP_LOAD=0`.
- the launcher exits `65` before exec with
  `blocked-seccomp-enforce-unimplemented`.

## Validation

- `py_compile`:
  - `run_wsta160_seccomp_full_rootfs_chroot_dry_run.py`
  - `test_server_distro_wsta160_seccomp_full_rootfs_chroot_dry_run.py`
- Focused WSTA158 + WSTA159 + WSTA160 tests: `7 tests OK`.
- Full server-distro regression: `553 tests OK`.
- WSTA160 proof generation from the real full source rootfs and real
  WSTA153/WSTA156/WSTA158 artifacts: pass.

## Next

WSTA161 should decide whether the next bounded step is still host-only
seccomp-loader implementation work or a separately gated live/chroot
observation.  Actual seccomp enforcement remains unproven and must stay behind
an explicit later gate.
