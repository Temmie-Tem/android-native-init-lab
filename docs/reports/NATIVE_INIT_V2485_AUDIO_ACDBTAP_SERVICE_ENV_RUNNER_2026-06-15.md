# NATIVE_INIT V2485 — ACDB tap service-env live runner

Date: 2026-06-15

## Decision

`v2485-acdbtap-service-env-live-dry-run`

V2485 implements the next live runner but does **not** execute it. It replaces the V2481
parallel manual-HAL route with the V2484 init-service environment module and adds the missing
AudioTrack APK install gate.

## Implementation

New public sources:

- `workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_live_handoff_v2485.py`
- `tests/test_native_audio_acdbtap_service_env_live_handoff_v2485.py`

Key behavior changes relative to V2481:

1. Uses the V2484 module and verifies the service rc override is visible after the Android
   post-module reboot.
2. Creates the capture directory before restarting audio.
3. Restarts `vendor.audio-hal` through init, not by launching a parallel manual process.
4. Requires every current `android.hardware.audio.service` PID to map `libacdbtap.so`; otherwise
   it aborts before playback.
5. Installs the private AudioTrack APK before playback and verifies
   `cmd package path com.a90.nativeinit.audio`.
6. Treats `am start` `Error type` / missing Activity output as a hard pre-capture failure.
7. Pulls and preserves the complete `/data/local/tmp/a90-acdb-tap/` capture directory.
8. Uninstalls the stimulus APK and removes the exact Magisk module before checked V2321 rollback.

## Partial-success policy

The operator policy is now encoded in the inherited artifact summarizer path:

- `captured-acdbtap-full-outbuf-set-no-4916` is operator-valuable partial success;
- it preserves the full ordered out-buffer record set;
- it does **not** count as a dead retry/fails-twice event.

No `out_len==4916` record is still a full success blocker, but `out_len>0` records without `4916`
are valuable because the operator can map size/order against the V2461 calibration sequence.

## Live boundary

Future live execution remains within the recoverable envelope:

- checked Android handoff only;
- temporary Magisk module under `/data/adb/modules/a90_acdbtap_service_env_v2484`;
- no `magisk --install-module`;
- no `setenforce 0`;
- no `service.sh`, `post-fs-data.sh`, or `sepolicy.rule`;
- no native `/dev/msm_audio_cal` calibration ioctl;
- no native speaker write;
- checked cleanup and rollback to V2321.

The dry-run reports:

```json
{
  "decision": "v2485-acdbtap-service-env-live-dry-run",
  "future_live_ready": true,
  "future_live_blockers": [],
  "ok": true
}
```

## Validation

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m py_compile \
    workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_live_handoff_v2485.py \
    tests/test_native_audio_acdbtap_service_env_live_handoff_v2485.py

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_native_audio_acdbtap_service_env_live_handoff_v2485 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_live_handoff_v2485.py

git diff --check
```

All passed.

## Next

The next meaningful unit is the preauthorized V2485 live run. The first hard checkpoint is whether
the V2484 rc override is visible and whether the init-managed `vendor.audio-hal` PID maps
`libacdbtap.so`. If that fails, stop with linker/SELinux/init evidence rather than replaying V2481's
manual parallel-HAL path.
