# NATIVE_INIT V2570 — ACDB pre-init-tail per-device capture live handoff

Date: 2026-06-16

## Scope

Run the V2569 live handoff using the V2568 own-process Android ACDB pre-init-tail
helper/preload. The unit stays measurement-only: fake `AUDIO_ALLOCATE_CALIBRATION`,
fake `AUDIO_DEALLOCATE_CALIBRATION`, fake/suppress any `AUDIO_SET_CALIBRATION`, capture
`acdb_ioctl` out-buffers, then checked rollback to V2321.

## Result

- V2569 wrapper decision: `v2569-send-audio-cal-v5-no-nonzero-capture-rollback-pass`
- V2490 engine decision: `v2490-helper-timeout-acdbtap-full-outbuf-set-no-4916-before-helper-exit-before-rollback-rollback-pass`
- Full payload success: `false`
- Partial success: `true` — the run captured two valid non-zero `acdb_ioctl` out-buffers and does not count toward the fails-twice dead-run budget.
- Rollback: `true`; V2321 final health passed with `selftest fail=0`.
- Private run directory: `workspace/private/runs/audio/v2570-acdb-preinit-perdevice-capture-20260616-121720`

## Key Observations

- `acdb_loader_init_v3()` reached the pre-init hook path and loaded ACDB files.
- Fake allocation worked through init: `25` `AUDIO_ALLOCATE_CALIBRATION` calls returned fake success for cal types `2,3,4,5,10,11,11,12,12,14,15,16,17,19,24,25,27,34,35,37,39,40,46,48,49`.
- No real `AUDIO_SET_CALIBRATION` was passed through; `real_audio_set_pass_through_count=0`.
- The hook entered `acdb_loader_send_common_custom_topology()`, but the real call returned `-92`.
- The hook patched the `is_initialized` flag successfully and reached `before_send_audio_cal_v5`.
- The helper did not reach `send_audio_cal_v5` return or the planned `exit_before_init_tail` marker before timeout.

## Captured ACDB Out-Buffers

Both buffers are non-zero and `ret==0`, but neither is the required 4916-byte topology nor a usable per-device manifest payload.

| seq | cmd | in_len | out_len | ret | sha256 |
| --- | --- | ---: | ---: | ---: | --- |
| `0x00000000` | `0x000131de` | `0` | `16` | `0` | `25513169f466cb63e98fe30731e7c577f76cb6b58283d4041b1c650d0bf0915c` |
| `0x00000001` | `0x00013262` | `8` | `4` | `0` | `fb5e512425fc9449316ec95969ebe71e2d576dbab833d61e2a5b9330fd70ee02` |

Raw ACDB buffers remain private under the run directory and are not committed.

## Boundary Check

- `A90_ACDB_FAKE_ALLOCATE=1` was set for the helper.
- `AUDIO_ALLOCATE_CALIBRATION` was intercepted as `fake-success`.
- `AUDIO_SET_CALIBRATION` was not passed through.
- No native replay, speaker write, or `/dev/msm_audio_cal` SET reached the kernel.
- Android rollback used the checked V2321 boot image, with boot readback SHA verification before returning to native init.

## Interpretation

V2570 is not a payload capture. It is an informative partial run that proves the fake-allocation
init path is viable and localizes the next blocker to the pre-init helper strategy:
`send_common_custom_topology()` returns `-92`, and forcing `send_audio_cal_v5()` from the
`send_common_custom_topology` hook reaches entry but does not return before timeout. The current
public send API route is therefore not a clean manifest-capture path.

The next unit should not rerun V2570 unchanged. It should either localize the exact
`send_audio_cal_v5()` stall/crash point with finer-grained interposition, or bypass the public
send API and call the lower-level ACDB GET command path directly once the required command/argument
layout is pinned.

## Validation

- Android handoff and artifact collection completed through the V2490 checked engine.
- Rollback to `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)` completed.
- Final native selftest: `pass=11 warn=1 fail=0`.
