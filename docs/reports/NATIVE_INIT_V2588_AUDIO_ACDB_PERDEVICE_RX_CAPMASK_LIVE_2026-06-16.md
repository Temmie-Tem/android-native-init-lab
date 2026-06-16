# NATIVE_INIT V2588 — ACDB per-device RX cap-mask live result

Date: 2026-06-16

## Scope

Live Android-good handoff using the V2587 runner and V2586 artifacts. The unit retested the
`acdb_loader_send_audio_cal_v5` fallback with `arg2=1` (RX capability bit set) after V2574/V2575
only exercised `arg2=0`. The run stayed measurement-only: fake audio-cal allocate preload enabled,
no native replay SET, no speaker write, raw artifacts private only, and rollback to V2321.

## Decision

- decision: `v2587-send-audio-cal-v5-no-per-device-records-rollback-pass`
- result: `failure-safe-negative`
- counts_toward_fails_twice: `true`
- run_dir: `workspace/private/runs/audio/v2587-acdb-perdevice-rx-capmask-20260616-152617`
- final native version: `0.9.285` / `v2321-usb-clean-identity-rodata`
- final selftest: `fail=0`

## Evidence

- Android handoff, helper staging, artifact pull, cleanup, recovery reboot, and V2321 rollback all
  completed.
- `ownget-run-helper` timed out after `120.0s`; rollback still completed successfully.
- preinit events reached `before_send_audio_cal_v5` with the V2586 `arg2=1` artifact.
- `acdbtap` recorded only the control marker after arming; no real `acdb_ioctl` call rows were
  captured.
- `ioctl_trace` recorded `53` events and `25` fake-success `AUDIO_ALLOCATE_CALIBRATION` calls.
- fake allocation snapshots included cal types `11`, `12`, `15`, and `16`, but all had
  `cal_size=0`; no payload buffers were captured.
- `AUDIO_SET_CALIBRATION` count was `0`, preserving the no-SET boundary.
- `helper_sigsegv=False`; this was a hang/timeout, not a crash.

## Interpretation

Setting the RX capability bit changes execution enough to enter a larger calibration allocation
path, but it still does not reach per-device `acdb_ioctl` GET output records before hanging. The
observed fake allocations are header/control allocation activity, not captured AFE/ASM/AUDPROC/VOL
payloads. A second identical live rerun is unlikely to add information.

## Next Step

Do host-side RE of `acdb_loader_send_audio_cal_v5` beyond the `(arg2 & 3)` gate to identify the
remaining preconditions for real GET dispatch: likely session/instance/context arguments or an
additional initialized-state object, not another blind `arg2=1` live retry. Keep native ACDB replay
blocked until real per-device bytes are captured and operator Gate-2 verifies them.

## Validation

- `python3 workspace/public/src/scripts/revalidation/a90ctl.py version`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest verbose`
- private `v2587-result.json` inspected for classification, rollback, event, and ioctl summaries
- raw ACDB payload bytes were not committed
