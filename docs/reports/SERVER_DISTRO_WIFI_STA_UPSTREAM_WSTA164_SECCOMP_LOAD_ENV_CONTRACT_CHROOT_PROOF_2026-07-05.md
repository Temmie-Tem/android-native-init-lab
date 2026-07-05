# WSTA164 Seccomp Load-Env Contract Chroot Proof Pass

Date: 2026-07-05 13:29 KST

## Verdict

WSTA164 adds the final host-side contract for forwarding the WSTA161 helper's
load environment from the service launcher.  The launcher still defaults to
check-only behavior.  Even in `apply` helper mode, it only forwards
`A90WSTA161_ALLOW_LOAD=1` and `A90WSTA161_LOAD_TOKEN` after a second explicit
launcher-side gate:

```text
A90_SERVICE_LAUNCH_SECCOMP_LOAD_GATE=WSTA164-ALLOW-SECCOMP-LOAD-ENV
```

The launcher does not hardcode the WSTA161 load token.  The proof never
supplies the correct WSTA161 token; the strongest path forwards a deliberate
wrong token and must still fail closed before
`A90WSTA161_SECCOMP_LOAD_ATTEMPT=1`.

This unit is host-only: it did not touch the device, flash, reboot, connect
Wi-Fi, run DHCP, open a public tunnel, mutate packet filters, write userdata,
load BPF, load a seccomp filter, or enforce seccomp.  It did run a
host-private `unshare -r chroot` proof only.

Result: PASS.  All three chroot paths exited `65` and no path emitted
`A90WSTA161_SECCOMP_LOAD_ATTEMPT=1`.

## Source Changes

- Updated
  `workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py`:
  - adds `A90_SERVICE_LAUNCH_SECCOMP_LOAD_GATE`.
  - adds `A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN`.
  - records `A90WSTA164_SECCOMP_LOAD_ENV_GATE=0|1`.
  - records token presence only as
    `A90WSTA164_SECCOMP_LOAD_TOKEN_PRESENT=1`; it does not log token values.
  - forwards `A90WSTA161_ALLOW_LOAD=1` and `A90WSTA161_LOAD_TOKEN=...` to the
    helper only after the WSTA164 gate is present and the launch token env is
    non-empty.
  - keeps the WSTA161 correct token out of the launcher text.
- Added
  `workspace/public/src/scripts/server-distro/run_wsta164_seccomp_load_env_contract_chroot_proof.py`.
- Added focused tests in
  `tests/test_server_distro_wsta164_seccomp_load_env_contract_chroot_proof.py`.
- Extended `tests/test_prepare_wsta3_sta_rootfs.py` for WSTA164 launcher
  metadata and token-literal absence.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta164-seccomp-load-env-contract-chroot-proof-20260705T1329KST/
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
wsta164-seccomp-load-env-contract-chroot-proof-pass
```

No WSTA164 load-env gate stdout:

```text
A90WSTA163_SECCOMP_HELPER_MODE=apply
A90WSTA164_SECCOMP_LOAD_ENV_GATE=0
A90WSTA161_LOADER_GATED_APPLY=1
A90WSTA161_SECCOMP_LOAD=0
A90WSTA161_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49
a90_seccomp_loader_decision=blocked-load-gate-required
a90_service_launcher_decision=blocked-seccomp-helper-apply-failed
```

WSTA164 load-env gate present, token absent stdout:

```text
A90WSTA163_SECCOMP_HELPER_MODE=apply
A90WSTA164_SECCOMP_LOAD_ENV_GATE=1
a90_service_launcher_decision=blocked-seccomp-helper-load-token-required
```

WSTA164 load-env gate present, wrong token stdout:

```text
A90WSTA163_SECCOMP_HELPER_MODE=apply
A90WSTA164_SECCOMP_LOAD_ENV_GATE=1
A90WSTA164_SECCOMP_LOAD_TOKEN_PRESENT=1
A90WSTA161_LOADER_GATED_APPLY=1
A90WSTA161_SECCOMP_LOAD=0
A90WSTA161_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49
a90_seccomp_loader_decision=blocked-load-token-required
a90_service_launcher_decision=blocked-seccomp-helper-apply-failed
```

## Checks

WSTA164 fail-closes unless:

- the proof is explicitly gated.
- source rootfs and all WSTA153/WSTA156/WSTA161 inputs are private.
- launcher metadata proves the WSTA164 load-env gate is present.
- launcher metadata proves load env forwarding is present.
- launcher metadata proves the WSTA161 correct token is not hardcoded.
- no-load-gate path invokes helper apply but keeps load env absent, causing
  `blocked-load-gate-required`.
- load-env-gate-without-token path blocks before helper output.
- load-env-gate-with-wrong-token path reaches helper apply and then blocks at
  `blocked-load-token-required`.
- no path emits `A90WSTA161_SECCOMP_LOAD_ATTEMPT=1`.
- no path reaches fake `setpriv`/exec.

## Validation

- `py_compile`:
  - `prepare_wsta3_sta_rootfs.py`
  - `run_wsta164_seccomp_load_env_contract_chroot_proof.py`
  - `test_prepare_wsta3_sta_rootfs.py`
  - `test_server_distro_wsta164_seccomp_load_env_contract_chroot_proof.py`
- Focused prepare-rootfs + WSTA163 + WSTA164 tests: `40 tests OK`.
- Full server-distro regression: `562 tests OK`.
- WSTA164 proof generation from the real full source rootfs and real
  WSTA153/WSTA156/WSTA161 artifacts: pass.

## Next

WSTA165 can now move to a bounded live-observation design for the staged
apply/load-env gates on device without supplying the correct WSTA161 load
token, or start the separate explicit design review for the first real
seccomp-load experiment.  Actual seccomp load/enforcement remains unproven.
