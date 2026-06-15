# NATIVE_INIT V2484 — ACDB tap init-service environment planner

Date: 2026-06-15

## Decision

`v2484-acdbtap-service-env-planner-host-only`

V2483 classified the V2481 live rerun as runner wiring failure: the AudioTrack APK was not
installed, and the manual `LD_PRELOAD` HAL process was not the init-managed audio service
handling Android audio. V2484 adds the next host-only building block: a temporary Magisk
measurement capsule that overlays the vendor audio HAL init rc with `setenv LD_PRELOAD`, so
future live work can require the **init-managed** `vendor.audio-hal` process itself to map
`libacdbtap.so`.

No Android boot, module activation, playback, native `/dev/msm_audio_cal` ioctl, native
speaker write, or calibration replay ran in this unit.

## Implementation

New public sources:

- `workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_planner_v2484.py`
- `tests/test_native_audio_acdbtap_service_env_planner_v2484.py`

Private materialized module:

- `workspace/private/builds/audio/v2484-acdbtap-service-env-module/`

The module contains:

- `module.prop`
- `README.md`
- `system/vendor/lib/libacdbtap.so`
- `system/vendor/etc/init/android.hardware.audio.service.rc`

The rc file is an otherwise faithful copy of the stock service definition plus:

```rc
# A90_ACDBTAP_V2484_RC_OVERRIDE
setenv LD_PRELOAD /vendor/lib/libacdbtap.so
setenv A90_ACDBTAP_DIR /data/local/tmp/a90-acdb-tap
```

It intentionally contains no `service.sh`, `post-fs-data.sh`, `system.prop`, or
`sepolicy.rule`.

## Design basis

- The local vendor rc defines `vendor.audio-hal` at
  `workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/etc/init/android.hardware.audio.service.rc`.
- Android init supports `setenv <name> <value>` as a service option and sets that environment in
  the launched process. Source: Android init README,
  <https://android.googlesource.com/platform/system/core/+/master/init/README.md>.
- Android init ignores duplicate service names unless an override mechanism is used, so a second
  service definition is not sufficient; the visible rc must replace the original path.
- Magisk module files under `system/vendor` are the documented module placement for replacing or
  injecting `/vendor` files. Source: Magisk Developer Guides,
  <https://topjohnwu.github.io/Magisk/guides.html>.

## Future live contract

V2485 should use this module, not the V2481 parallel manual process route:

1. Install the V2484 module directly under its exact `/data/adb/modules/...` path.
2. Reboot Android for Magisk mount activation.
3. Verify `/vendor/etc/init/android.hardware.audio.service.rc` contains
   `A90_ACDBTAP_V2484_RC_OVERRIDE`, `setenv LD_PRELOAD`, and `setenv A90_ACDBTAP_DIR`.
4. Create `/data/local/tmp/a90-acdb-tap` before restarting audio.
5. Restart `vendor.audio-hal` through init and require every current
   `android.hardware.audio.service` PID to map `libacdbtap.so`; abort before playback if any PID
   does not.
6. Install the private AudioTrack APK before `am start`; fail fast if `cmd package path
   com.a90.nativeinit.audio` is absent or `am start` reports `Error type 3`.
7. Pull the full `/data/local/tmp/a90-acdb-tap/` directory and preserve all out-buffer records.

If a future run captures out-buffer records but no `out_len==4916`, classify it as the operator's
partial success case (`captured-acdbtap-full-outbuf-set-no-4916`), preserve the run, and do not
count it as a dead retry.

## Validation

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m py_compile \
    workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_planner_v2484.py \
    tests/test_native_audio_acdbtap_service_env_planner_v2484.py

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_native_audio_acdbtap_service_env_planner_v2484 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_service_env_planner_v2484.py \
    --materialize-module

git diff --check
```

All passed. The materialized private module reports `ok=true` and `command_safety.ok=true`.

## Boundaries

- Raw ACDB payload bytes remain private.
- No generated module files are committed.
- No native calibration ioctl is live-enabled.
- No SELinux permissive or policy change is introduced.
- The next live run must still roll back to V2321 and end with native `selftest fail=0`.
