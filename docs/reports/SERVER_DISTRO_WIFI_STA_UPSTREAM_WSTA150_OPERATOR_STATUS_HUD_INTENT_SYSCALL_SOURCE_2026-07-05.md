# WSTA150 Operator Status HUD Intent Syscall Source Pass

Date: 2026-07-05 11:17 KST

## Verdict

WSTA150 folds the WSTA149 D-public HUD intent-producer syscall trace proof into
the operator server-status bundle.  This was a host-only source/status unit.  It
did not touch the device, flash, reboot, switch root, connect Wi-Fi, start DHCP,
open a public tunnel, mutate packet filters, write userdata, or run a live
service.

Result: PASS.  WSTA108 now reports the HUD presenter state as
`DPUBLIC_HUD_INTENT_SYSCALL_TRACE_LIVE_PROVEN` when the durable presenter
restart proof and the WSTA149 HUD intent syscall proof are supplied and
recompute cleanly.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta149_dpublic_hud_intent_syscall_trace_summary.py`.
  It re-reads the private WSTA149 live result and emits a compact
  `wsta149_dpublic_hud_intent_syscall_trace_live.json` proof with no device
  action.
- Extended
  `workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py`
  with `--wsta149-hud-intent-syscall-proof-json`.
- Added WSTA108 tests for a valid WSTA149 proof, a non-pass proof, and an
  incomplete proof that must block even when the supplied decision says pass.
- Added focused tests for the WSTA149 summary proof generator.

## Proof Folded

The generated WSTA149 summary decision was:

```text
wsta149-dpublic-hud-intent-syscall-trace-live-pass
```

Summary run:

```text
workspace/private/runs/server-distro/wsta150-wsta149-hud-intent-syscall-summary-20260705T1114KST/
```

Source live run:

```text
workspace/private/runs/server-distro/wsta149-dpublic-hud-intent-syscall-trace-live-20260705T1058KST/
```

The proof includes:

- service `dpublic-hud`, scope `hud-intent-producer-only`.
- UID/GID `3904/3904`.
- `NoNewPrivs=1` and zero effective capabilities.
- public exposure default-off.
- native presenter ownership preserved.
- intent path `/run/a90-dpublic/hud-intent.json`, sequence `14901`.
- atomic path observed through `fsync` plus `renameat`.
- no network syscalls.
- no `ioctl` syscall and no DRM trace content.
- trace artifacts saved privately.
- syscall profile count `22`.

## Operator Status Result

Private WSTA108 status regeneration decision:

```text
wsta108-operator-server-status-source-pass
```

Status run:

```text
workspace/private/runs/server-distro/wsta150-operator-status-hud-intent-syscall-20260705T111516KST/
```

Key resulting state:

- Server state: `SERVER_PROFILE_READY_DEFAULT_OFF`.
- HUD presenter state: `DPUBLIC_HUD_INTENT_SYSCALL_TRACE_LIVE_PROVEN`.
- `hud_intent_syscall_trace_live_proven=true`.
- `hud_intent_syscall_no_network=true`.
- `hud_intent_syscall_no_drm=true`.
- `hud_intent_syscall_atomic_write=true`.
- D-public HUD is no longer listed in remaining syscall profiles.
- Remaining syscall profile: `dropbear-admin-usb`.
- Public exposure remains default-off.
- No public URL value or secret value is present in the public summary or
  generated markdown.

The operator next actions now include:

```text
continue-containment-hardening-or-derive-hud-seccomp-policy
```

The old HUD-specific next action
`profile-dpublic-hud-syscalls-or-continue-containment-hardening` is retired when
the WSTA149 proof is supplied and recomputes cleanly.

## Validation

- `py_compile`:
  - `run_wsta108_operator_server_status.py`
  - `run_wsta149_dpublic_hud_intent_syscall_trace_summary.py`
  - `test_server_distro_wsta108_operator_server_status.py`
  - `test_server_distro_wsta149_dpublic_hud_intent_syscall_trace_summary.py`
- Focused WSTA108 + WSTA149 summary unit tests: `47 tests OK`.
- Full server-distro WSTA regression: `476 tests OK`.
- WSTA149 summary generation from the live WSTA149 private result: pass.
- WSTA108 operator status regeneration with the WSTA149 proof: pass.

During status regeneration, an older WSTA94 input was rejected with
`wsta108-blocked-wsta94-packet-filter-proof-not-pass`.  The final pass used the
known PASS WSTA94 proof:

```text
workspace/private/runs/server-distro/wsta94-packet-filter-live-20260704T143227Z/wsta94_result.json
```

## Safety

This unit was source/status-only.  The live device remained on the existing
V3402 resident image from the WSTA149/WSTA147 line; no new device operation was
performed for WSTA150.

## Next

Continue containment hardening.  The HUD intent-producer syscall profile is now
live-proven and folded into status, so the next useful choices are deriving a
HUD seccomp policy from the live baseline or collecting the remaining
`dropbear-admin-usb` syscall profile before broader seccomp enforcement.
