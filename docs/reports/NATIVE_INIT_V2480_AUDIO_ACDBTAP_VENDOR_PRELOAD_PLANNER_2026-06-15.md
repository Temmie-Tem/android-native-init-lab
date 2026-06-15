# V2480 — ACDB tap vendor-path preload planner

## Purpose

V2479 proved that the V2475 `libacdbtap.so` interposer cannot be loaded into
`android.hardware.audio.service` from `/data/local/tmp`: Android's vendor linker
namespace permits `/odm`, `/vendor`, and `/system/vendor`, but rejects the tmp
path before the HAL starts. V2480 is a host-only planner for a temporary
Magisk/systemless measurement capsule that exposes the same 32-bit interposer at
a vendor namespace-visible path.

This is still measurement-only. It does not run playback, install a module, touch
native calibration ioctls, or replay any ACDB payload.

## Module shape

Generated private module directory:

- `workspace/private/builds/audio/v2480-acdbtap-vendor-preload-module/`
- module id: `a90_acdbtap_vendor_preload_v2480`
- payload: `system/vendor/lib/libacdbtap.so`
- candidate preload paths after Android/Magisk mount:
  - `/vendor/lib/libacdbtap.so`
  - `/system/vendor/lib/libacdbtap.so`

The capsule intentionally contains no:

- `service.sh`
- `post-fs-data.sh`
- `system.prop`
- `sepolicy.rule`
- native ACDB replay code

The helper uses direct exact-path staging under
`/data/adb/modules/a90_acdbtap_vendor_preload_v2480` and avoids
`magisk --install-module`, so cleanup can remove the exact module path and the
matching `/data/adb/modules_update/...` path only.

## Command plan

The generated command plan is staged for a future Android handoff runner:

1. Create a shell-writable staging tree under `/data/local/tmp/a90-acdbtap-v2480`.
2. Push `module.prop`, `README.md`, and `system/vendor/lib/libacdbtap.so`.
3. Install the exact module directory via `su -mm -c`.
4. Reboot Android so Magisk mounts the systemless vendor path.
5. Verify candidate preload paths with `ls -lZ` and `sha256sum`.
6. Run the V2477 ACDB tap playback capture only if the HAL maps-confirmation
   shows `libacdbtap.so` from one verified candidate path.
7. Remove only the exact module/run paths before rollback.

## Safety boundary

The command safety scanner rejects:

- `AUDIO_SET_CALIBRATION`
- `AUDIO_ALLOCATE_CALIBRATION`
- `tinyplay`
- `setenforce 0`
- broad `/data/adb/modules` deletion
- `magisk --install-module`
- module service/policy scripts in the command plan

A future live runner must still stop before playback if the HAL maps do not show
`libacdbtap.so` loaded from a verified vendor-visible path. It must pull the full
`/data/local/tmp/a90-acdb-tap/` directory and preserve every ordered `out_len>0`
record privately.

## Acceptance policy carried forward

A full success is `captured-acdbtap-full-outbuf-set-with-4916`: complete ordered
ACDB out-buffer set plus the 4916-byte topology record.

`captured-acdbtap-full-outbuf-set-no-4916` is a partial success, not a dead run.
It still preserves per-device AFE/ASM/ADM/VOL calibration payloads for operator
mapping and must not count toward fails-twice retry accounting.

## Validation

Commands run:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m py_compile \
    workspace/public/src/scripts/revalidation/native_audio_acdbtap_vendor_preload_planner_v2480.py \
    tests/test_native_audio_acdbtap_vendor_preload_planner_v2480.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_native_audio_acdbtap_vendor_preload_planner_v2480 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_vendor_preload_planner_v2480.py
```

Observed planner summary:

```json
{
  "decision": "v2480-acdbtap-vendor-preload-planner",
  "module_ok": true,
  "ok": true,
  "command_safety": {
    "findings": [],
    "missing_required_needles": [],
    "ok": true
  }
}
```

## Next unit

Implement the V2481 Android handoff/live runner that uses this planner to stage
the temporary module, reboots Android for Magisk mount, verifies the vendor path,
then reruns the ACDB tap capture. If vendor-path preload is still blocked, stop
and report before playback.
