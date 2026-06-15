# NATIVE_INIT_V2532_AUDIO_ACDB_ALLOCATE_IOCTL_TRACE_LIVE_2026-06-16

## Scope

V2532 attempted the first live Android handoff for the V2531 `ioctl()` trace preload around the own-process ACDB GET helper. The target measurement was the existing ACDB init path only: observe `/dev/msm_audio_cal` `AUDIO_ALLOCATE_CALIBRATION` ioctl return/errno and AVC evidence around `acdb_loader_init_v3`.

This run did not reach that target. Android booted and Magisk root was confirmed, but ADB transport closed during the first `ownget-setup` shell step before any helper or trace preload was staged.

## Safety Boundary

- No native ACDB replay was attempted.
- No `/dev/msm_audio_cal` SET ioctl was issued.
- No ACDB GET helper was staged or executed.
- No ioctl trace preload was staged or executed.
- Rollback to V2321 completed through the checked helper.
- Final native V2321 health check: `selftest fail=0`.

## Private Evidence

- Run directory: `workspace/private/runs/audio/v2532-acdb-allocate-ioctl-trace-20260616-054619/`
- Android boot image used for handoff: private run-local sealed copy only.
- Public raw payloads: none.
- Private ACDB output artifacts: none produced.

## Live Result

Step summary:

| Step | Result | Evidence |
| --- | --- | --- |
| `flash-android` | pass | Android boot-complete observed; Magisk `su -c id` returned `uid=0(root)` |
| `android-post-handoff-settle-0/1/2` | pass | `adb wait-for-device`, boot-complete recheck, root id check all passed |
| `ownget-setup` | fail | `stderr`: `error: closed` |
| rollback to V2321 | pass | boot readback SHA matched; native `version` reports `0.9.285`; `selftest fail=0` |

Runner decision:

```text
v2490-acdb-ownprocess-get-live-started-rollback-pass
```

The result is `ok=false` because the measurement did not run. It is not an ACDB negative result and must not count as evidence for or against `AUDIO_ALLOCATE_CALIBRATION`.

## Interpretation

This is an Android ADB transport settle race after boot handoff, not an ACDB or SELinux finding. The failed command was the setup shell that would have created `/data/local/tmp/a90-acdb-ownget`; it failed before staging the helper, dependency libraries, or `liba90_ioctl_trace_v2531.so`.

No `ioctl-trace-events.jsonl`, ACDB event JSONL, dmesg AVC filter, or logcat AVC filter exists for this run because setup stopped before the remote work directory was created.

## Required Follow-up

The next live attempt must not rerun the same route unchanged. Add a guarded ADB transport retry/resettle around the early Android staging phase, especially `ownget-setup` and the first push steps:

1. On `adb` stderr matching `error: closed`, `no devices/emulators found`, or `device offline`, run `adb wait-for-device` and recheck `sys.boot_completed` plus `su -c id`.
2. Retry the failed early staging step once or twice with bounded delay.
3. If the retry still fails, rollback and report as transport-blocked.
4. Do not retry ACDB helper execution itself after it starts; helper execution remains one-shot for measurement integrity.

Only after this transport guard is in place should the V2531 trace preload be rerun to capture the exact `AUDIO_ALLOCATE_CALIBRATION` errno and AVC lines.

## Validation

Post-rollback native checks run after V2532:

```text
version: 0.9.285 build=v2321-usb-clean-identity-rodata
selftest: pass=11 warn=1 fail=0
```
