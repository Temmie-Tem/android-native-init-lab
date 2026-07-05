# WSTA148 Operator Status HUD Restart Source Pass

Date: 2026-07-05 10:47 KST

## Verdict

WSTA148 folds the WSTA147 D-public HUD presenter restart/stale-cleanup live
proof into the operator server-status bundle.  This was a host-only source/status
unit.  It did not touch the device, flash, reboot, switch root, connect Wi-Fi,
start DHCP, open a public tunnel, mutate packet filters, or write userdata.

Result: PASS.  WSTA108 now reports the HUD presenter state as
`DPUBLIC_HUD_DURABLE_PRESENTER_RESTART_LIVE_PROVEN` when both the WSTA144
handoff proof and WSTA147 restart proof are supplied and recompute cleanly.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta147_dpublic_hud_restart_live_summary.py`.
  It re-reads the private WSTA147 live transcripts and emits
  `wsta147_dpublic_hud_restart_live.json` with no device action.
- Extended
  `workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py`
  with `--wsta147-hud-presenter-restart-proof-json`.
- Added WSTA108 tests for a valid WSTA147 restart proof and an incomplete proof
  that must block even when the supplied decision says pass.

## Proof Folded

The generated WSTA147 summary decision was
`wsta147-dpublic-hud-restart-live-pass`.

The proof includes:

- V3402 candidate:
  `A90 Linux init 0.11.158 (v3402-dpublic-hud-presenter-restart-policy)`.
- Boot SHA256:
  `57821e94857cb58b397c737a73d5f85381329f5e9ec8a6b55dc7d5dbb6a7d3f1`.
- Checked-helper flash and post-boot verification clean.
- Pre-restart `sequence=14701` presented with `present_rc=0` and DRM fd held.
- Restart stop/start proved with `restart.stop_rc=0`,
  `restart.start_rc=0`, and `restart.done=1`.
- Post-restart `sequence=14702` presented with `present_rc=0` and DRM fd held.
- Fake stale pidfile `999999` was unlinked by the start path.
- Final service status stopped and final V3402 health clean.

## Operator Status Result

Private WSTA108 status regeneration decision:
`wsta108-operator-server-status-source-pass`.

Key resulting state:

- Server state: `SERVER_PROFILE_READY_DEFAULT_OFF`.
- HUD presenter state:
  `DPUBLIC_HUD_DURABLE_PRESENTER_RESTART_LIVE_PROVEN`.
- `handoff_live_proven=true`.
- `restart_live_proven=true`.
- `durable_restart_live_proven=true`.
- `hud_presenter_restart_stop_start_proven=true`.
- `hud_presenter_restart_post_present_proven=true`.
- `hud_presenter_stale_pid_cleanup_proven=true`.
- Remaining HUD presenter live proof:
  `optional HUD syscall trace profile before seccomp enforcement`.
- Public exposure remains default-off.
- No public URL value or secret value is present in the public summary or
  generated markdown.

The operator next action is now:
`profile-dpublic-hud-syscalls-or-continue-containment-hardening`.

## Validation

- `py_compile`:
  - `run_wsta108_operator_server_status.py`
  - `run_wsta147_dpublic_hud_restart_live_summary.py`
  - `test_server_distro_wsta108_operator_server_status.py`
- Focused WSTA108 unit tests: `41 tests OK`.
- Full server-distro WSTA regression: `462 tests OK`.
- WSTA147 summary generation from the live WSTA147 private transcripts: pass.
- WSTA108 operator status regeneration with WSTA144 and WSTA147 proofs: pass.

## Safety

This unit was source/status-only.  The live device remained on the WSTA147
live-passed V3402 resident image; no new device operation was performed for
WSTA148.

## Next

Choose between optional HUD syscall trace profiling before seccomp enforcement
and broader containment hardening.  Do not repeat HUD handoff or restart live
proofs unless a regression appears.
