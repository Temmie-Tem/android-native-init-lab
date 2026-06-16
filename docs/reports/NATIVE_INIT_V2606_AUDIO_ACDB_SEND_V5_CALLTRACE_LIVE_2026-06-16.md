# V2606 — ACDB `send_audio_cal_v5` calltrace preload live result

Date: 2026-06-16

## Scope

V2606 ran the V2592 rollbackable Android-good own-process ACDB capture path with the V2605
combined preload override. The goal was metadata-only observability around
`acdb_loader_send_audio_cal_v5` after V2604 proved that the corrected per-device call reached
`before_send_audio_cal_v5` and then hung before any armed `acdb_ioctl` rows appeared.

This unit remained measurement-only:

- fake `AUDIO_ALLOCATE_CALIBRATION` remained enabled;
- no real `AUDIO_SET_CALIBRATION` replay was allowed;
- no native speaker write or route change was performed;
- raw ACDB bytes, if any, were private-only;
- Android handoff rolled back to V2321 through the checked helper.

## Inputs

- Runner: `workspace/public/src/scripts/revalidation/native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592.py`
- Helper: `workspace/private/builds/audio/v2605-acdb-send-v5-calltrace-combined-preload-build-only/bin/a90_acdb_perdevice_rx_capmask_argorder_exec_linked_v2605`
- Helper SHA256: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
- Preload: `workspace/private/builds/audio/v2605-acdb-send-v5-calltrace-combined-preload-build-only/bin/liba90_acdb_send_v5_calltrace_combined_preload_v2605.so`
- Preload SHA256: `b2cc5735813de666c2705f5a6b7895c3fcc71361e57afc780a32cf1fd0ca3d07`
- Exact live gate used: `AUD-ACDB-V2592-perdevice-rx-capmask-argorder go: one-shot send_audio_cal_v5 arg2=1 corrected-stack-order per-device capture on Android, fake allocate preload, no SET replay, no speaker write, rollback to V2321`

## Result

Private run directory:

- `workspace/private/runs/audio/v2592-acdb-perdevice-rx-capmask-argorder-20260616-180830`

Top-level decision:

- `v2592-ownprocess-helper-sigsegv-no-events-rollback-pass`

Summary:

| Field | Value |
| --- | --- |
| `ok` | `false` |
| V2606 classification | `v2573-ownprocess-helper-sigsegv-no-events` |
| `send_audio_cal_v5_reached` | `false` |
| V2605 calltrace rows | none |
| `acdbtap_call_row_count` | `0` |
| `acdbtap_control_row_count` | `0` |
| raw ACDB files | `0` |
| target 4916 rows | `0` |
| helper rc | `139` |
| helper stderr | `Segmentation fault` |
| rollback | passed to V2321 |

## Evidence

The staged hashes matched the intended V2605 artifacts on-device:

- helper: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
- preload: `b2cc5735813de666c2705f5a6b7895c3fcc71361e57afc780a32cf1fd0ca3d07`

The helper crashed before writing stdout or any ACDB/calltrace event files:

- `ownget.rc` = `139`
- `ownget.stderr.txt` = `Segmentation fault`
- `acdbtap-raw-sha256s.txt` is empty
- `acdb-v2605-send-v5-calltrace-events.jsonl` is absent

The Android crash log attributes the fault to the V2605 combined preload:

```text
Fatal signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0xff30dff8 in tid 3926 (a90_acdb_ownpro), pid 3926 (a90_acdb_ownpro)
Cmdline: /data/local/tmp/a90-acdb-ownget/a90_acdb_ownprocess_get_exec_linked_v2529
#00 pc 00003e38  /data/local/tmp/a90-acdb-ownget/liba90_acdb_combined_preload_v2538.so
```

Symbol mapping of the V2605 preload maps `0x3e38` to the new V2605 tracer resolver:

```text
00003e38   360 FUNC LOCAL DEFAULT 9 a90_resolve
00003d70   200 FUNC GLOBAL DEFAULT 9 pthread_mutex_lock
000041b0   200 FUNC GLOBAL DEFAULT 9 pthread_mutex_unlock
00004278   244 FUNC GLOBAL DEFAULT 9 __android_log_print
```

This means the V2605 imported-call tracer itself regressed the process before the helper reached
its previous V2604 point (`before_send_audio_cal_v5`). The most likely mechanism is unsafe
interposition of `pthread_mutex_lock` / `pthread_mutex_unlock` during dynamic-linker or libc
initialization: `pthread_mutex_lock()` calls `a90_resolve()`, and `a90_resolve()` calls `dlsym()`
while the mutex hook is already active. If `dlsym()` or the loader needs a pthread mutex before the
real mutex symbol is installed, the hook cannot safely delegate and can destabilize the process.

This is a tracer regression, not new evidence against the ACDB per-device path.

## Rollback / cleanup

The live runner completed cleanup and rollback:

- `/data/local/tmp/a90-acdb-ownget` and `/data/local/tmp/a90-acdb-tap` were removed by the runner.
- Android rebooted to recovery.
- V2321 was flashed through `native_init_flash.py` with expected SHA/version checks.
- Rollback step `rollback-v2321` returned `ok=True`.

## Decision

V2606 is classified as:

- `tracer-regression-before-send-v5`

It does not count as a meaningful retry of the V2604 per-device frontier because the new tracer
crashed earlier than the V2604 combined preload. Do not iterate further with pthread/log imported-call
interposition in this preload.

## Next unit

Build a narrower V2607 preload that keeps the V2603/V2604 working composition but removes the risky
`pthread_mutex_*` and `__android_log_print` interposers. If more observability is required, wrap only
`acdb_loader_send_audio_cal_v5` itself and log entry/return with raw syscalls, or add explicit helper
stage markers around the call. The next live test should re-establish the V2604 baseline first:

1. init reaches the initialized-flag patch;
2. capture is armed only after init;
3. helper reaches `before_send_audio_cal_v5`;
4. no real `AUDIO_SET_CALIBRATION` passthrough occurs;
5. rollback to V2321 passes.
