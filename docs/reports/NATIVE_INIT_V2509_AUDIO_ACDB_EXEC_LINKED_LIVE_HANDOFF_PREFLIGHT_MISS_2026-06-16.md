# NATIVE_INIT V2509 — audio ACDB exec-linked live handoff preflight miss

## Decision

`v2509-exec-linked-helper-not-run-flash-android-from-native-missing-rollback-pass`

V2509 attempted to run the V2508 exec-linked own-process ACDB GET helper through
the existing checked Android handoff runner.  The helper did **not** execute.  The
run stopped at the initial Android flash step because the live command was invoked
without `--from-native` while the device was resident in V2321 native init.

This is a handoff invocation error, not evidence against the exec-linked ACDB
helper, the V2506 dependency closure, or the own-process direct-GET path.

## Inputs

Helper:

- Path: `workspace/private/builds/audio/v2508-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2508`
- SHA256: `73c2ab686e2462e59c09c27b2f0e0d3ce8d84c2a3a814b0f787c3faba6bc1bda`
- Mode narrowed before live attempt: `0700`

Dry-run result before live:

- `live_ready=true`
- `live_blockers=[]`
- `command_safety.ok=true`
- ACDB dependency source: `v2506-vendor-ext4-closure`
- helper SHA matched expected value

Private run directory:

- `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-032955/`

The runner identity still reports `V2490` because it is the inherited live runner;
this report records the new operational iteration as V2509.

## What happened

The runner sealed the Android boot candidate correctly, then called:

```text
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  <run-dir>/android_boot_0600.img \
  --expect-sha256 c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b \
  --expect-readback-sha256 c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b \
  --expect-android-magic \
  --post-flash-target android-adb \
  --android-root-check \
  --android-timeout 240.0 \
  --adb adb
```

Because the device was in native init and the command did not include
`--from-native`, `native_init_flash.py` waited for recovery ADB without first
asking native init to reboot to recovery:

```text
phase.native_init_flash.wait_recovery_adb.elapsed_sec=180.894 ok=0
error: ADB state timeout; wanted=['recovery'] last=<none>
```

No Android boot occurred.  No helper was pushed or executed.  No
`acdb_loader_init_v3()` or `acdb_ioctl()` call happened.

## Rollback and health

The runner then used its fallback path:

1. Android ADB was unavailable.
2. Native bridge probe succeeded.
3. It retried rollback with `native_init_flash.py ... --from-native`.
4. V2321 flashed and verified successfully.

Final checked state after rollback:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

Rollback result:

- `rolled_back=true`
- `rollback_fallback=from-native`
- final V2321 `selftest fail=0`

## Classification

This run is **not** an ACDB own-process negative result.

- It does not count against the fails-twice ACDB helper budget.
- It does not test the V2508 startup DT_NEEDED hypothesis.
- It only proves that the live handoff invocation must include `--from-native`
  when starting from the resident native-init baseline.

## Boundaries preserved

Preserved:

- no in-HAL injection;
- no wrapper-exec Magisk module;
- no HAL restart;
- no AudioTrack/playback;
- no native speaker write;
- no `/dev/msm_audio_cal` open/ioctl;
- no `0xC00461CB` calibration SET ioctl;
- no raw ACDB payload committed;
- rollback target V2321 restored with `selftest fail=0`.

## Validation

Host checks after the run:

```text
python3 workspace/public/src/scripts/revalidation/a90ctl.py --timeout 8 version
python3 workspace/public/src/scripts/revalidation/a90ctl.py --timeout 8 selftest
```

Both passed against V2321.

## Next unit

V2510 should rerun the same V2508 helper through the same runner, but explicitly
include `--from-native`:

```text
PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness \
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  --run-live \
  --from-native \
  --helper-path workspace/private/builds/audio/v2508-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2508 \
  --helper-sha256 73c2ab686e2462e59c09c27b2f0e0d3ce8d84c2a3a814b0f787c3faba6bc1bda \
  --helper-timeout 90 \
  --adb-command-timeout 120 \
  --adb-pull-timeout 180
```

If V2510 reaches Android and the helper executes, classify the result on the ACDB
own-process axis.  If it blocks before helper execution again, classify it as a
handoff/runner issue, not as an ACDB GET failure.
