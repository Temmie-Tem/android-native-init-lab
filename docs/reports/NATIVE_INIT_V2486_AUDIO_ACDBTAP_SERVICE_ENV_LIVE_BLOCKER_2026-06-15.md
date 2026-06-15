# NATIVE_INIT V2486 — ACDB tap service-env live blocker and transfer hardening

Date: 2026-06-15

## Scope

Continue the ACDB `acdb_ioctl` interposition capture route after V2485 added the
init-managed service-env runner. This unit is still measurement-only:

- no native `/dev/msm_audio_cal` calibration ioctl
- no native `tinymix`/`tinyplay`
- no silent `setenforce 0` / policy relaxation
- transient Magisk capsule only
- checked rollback to V2321 after each Android handoff

Operator policy preserved: `captured-acdbtap-full-outbuf-set-no-4916` remains an
operator-valuable partial success and does not count as a dead fails-twice run.
No run in this unit reached ACDB capture, so that branch did not trigger.

## Inputs

- Runner: `workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_live_handoff_v2485.py`
- Planner/module source: `workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_planner_v2484.py`
- Prior committed runner report: `docs/reports/NATIVE_INIT_V2485_AUDIO_ACDBTAP_SERVICE_ENV_RUNNER_2026-06-15.md`
- Private live runs:
  - `workspace/private/runs/audio/v2485-acdbtap-service-env-live-20260615-234534`
  - `workspace/private/runs/audio/v2485-acdbtap-service-env-live-20260615-235121`
  - `workspace/private/runs/audio/v2485-acdbtap-service-env-live-20260615-235800`

Raw logs and payload-capable artifacts remain private.

## Live result summary

| Run | Result | Interpretation | Rollback |
| --- | --- | --- | --- |
| `234534` | `v2485-module-push-2 failed rc=1` after Android/root handoff | ADB transport failure before module install; not an ACDB negative | V2321 selftest `fail=0` |
| `235121` | module installed and overlay visible, but preload not confirmed | init parsed a duplicate `vendor.audio-hal` service and ignored the overlaid service definition; original HAL kept running without `LD_PRELOAD` | V2321 selftest `fail=0` |
| `235800` | same preload-not-confirmed result after adding `override` | overlay file contained `override`, but Samsung/this init path still logged `ignored duplicate definition of service 'vendor.audio-hal'`; service was restarted, but the new HAL still did not map `libacdbtap.so` | V2321 selftest `fail=0` |

## Code changes

1. Hardened the small Magisk module `adb push` sequence:
   - if `adb push` returns nonzero after printing a successful transfer line, verify the exact
     remote SHA-256 and continue only if it matches;
   - if SHA does not match, wait for ADB once, retry the push once, and verify again;
   - this is transport recovery only, not ACDB capture retry logic.
2. Added `override` to the temporary `vendor.audio-hal` service definition and made the post-boot
   verification grep for it explicitly.
3. Added unit coverage for the ADB-push SHA recovery helpers and the `override` dry-run token.

## Evidence

### ADB push failure was infrastructure-only

The first run booted Android and obtained Magisk root, then failed while pushing the tap `.so`:

```text
workspace/private/builds/audio/v2484-acdbtap-service-env-module/system/vendor/lib/libacdbtap.so: 1 file pushed, 0 skipped. ...
adb: error: failed to read copy response
```

The runner rolled back to V2321 and final native `selftest` was `fail=0`. No module was installed;
no playback or ACDB capture was attempted.

### Service-env overlay was visible but not active in init

The later runs proved the module overlay itself was visible after reboot:

```text
/vendor/lib/libacdbtap.so ... 7bf64bb04530202a8dc859db0826cd399ff34d51ea4628eb586808de82968be4
/vendor/etc/init/android.hardware.audio.service.rc
# A90_ACDBTAP_V2484_RC_OVERRIDE
    override
    setenv LD_PRELOAD /vendor/lib/libacdbtap.so
    setenv A90_ACDBTAP_DIR /data/local/tmp/a90-acdb-tap
```

But kernel/init logs showed the overlaid service definition did not replace the original service:

```text
init: /vendor/etc/init/android.hardware.audio.service.rc: 1: ignored duplicate definition of service 'vendor.audio-hal'
```

Android init documentation states `setenv` sets an environment variable for the launched process and
that `override` is the service option intended to replace a previous service definition; this device
still ignored the duplicate in the Magisk-overlay parse path. Source:
https://android.googlesource.com/platform/system/core/+/master/init/README.md

### Service stop/start did not provide preload

`ctl.stop vendor.audio-hal` was processed and init restarted the service, but because the original
service definition remained authoritative, the restarted PID did not map `libacdbtap.so`:

```text
A90_ACDBTAP_SERVICE_STALE_PIDS <pid>
init: Sending signal 9 to service 'vendor.audio-hal' ...
init: Control message: Processed ctl.stop for 'vendor.audio-hal' ...
init: starting service 'vendor.audio-hal'...
```

No playback was run after this gate failed. The runner correctly aborted before the AudioTrack
stimulus.

## Classification

- `234534`: `runner-transport-failure-before-module-install`, not ACDB negative.
- `235121`: `service-env-duplicate-ignored`, not ACDB negative.
- `235800`: `service-env-override-ignored`, not ACDB negative.

These are injection-route blockers. They did not test whether `acdb_ioctl` emits the target or
operator-valuable non-4916 payload set.

## Next route

The init `.rc` service-env overlay path is exhausted for this device unless a lower-level init import
ordering trick is found. The next meaningful unit should switch to the operator-spec fallback class:

1. design a temporary wrapper-exec Magisk capsule for `/vendor/bin/hw/android.hardware.audio.service`;
2. preserve the original HAL binary under a second vendor-visible path;
3. have the wrapper set `LD_PRELOAD=/vendor/lib/libacdbtap.so` and `A90_ACDBTAP_DIR`, then `execve`
   the preserved original binary;
4. first run host-only/build-only checks, then a live preflight that only verifies file contexts,
   process domain, and maps before any AudioTrack stimulus.

Key risk for that next unit: the overlaid executable path must keep the HAL exec context/domain.
If Magisk labels the wrapper as `system_file` rather than `hal_audio_default_exec`, init execution or
HAL registration may fail. That must be measured before playback.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_live_handoff_v2485.py`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdbtap_service_env_live_handoff_v2485`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_planner_v2484.py`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_live_handoff_v2485.py`
- `git diff --check`
- Live rollback health after each run: V2321, `selftest fail=0`.
