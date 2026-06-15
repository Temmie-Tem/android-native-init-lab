# NATIVE_INIT V2487 — ACDB tap wrapper-exec planner

## Decision

`v2487-acdbtap-wrapper-exec-planner-host-only`

Host-only preparation passed. V2487 builds a private transient Magisk module for the
next Android-good ACDB tap injection route, but performs no device, Android, playback,
or native calibration action.

## Why this route

V2486 exhausted the service-rc environment route: Magisk overlay made the replacement
`android.hardware.audio.service.rc` visible and it contained `override` plus `setenv`,
but Android init still logged the stock vendor service as a duplicate and ignored the
overlay definition. The HAL restarted without `libacdbtap.so` mapped. That is an
injection-route blocker, not negative evidence about ACDB payload capture.

V2487 avoids the duplicate-service rc path. It keeps Android init's stock
`vendor.audio-hal` service definition and overlays only the executable path:

- `/vendor/bin/hw/android.hardware.audio.service` → freestanding wrapper executable
- `/vendor/bin/hw/android.hardware.audio.service.a90orig` → preserved stock HAL binary
- `/vendor/lib/libacdbtap.so` → V2475 `acdb_ioctl` interposer

The wrapper prepends:

- `LD_PRELOAD=/vendor/lib/libacdbtap.so`
- `A90_ACDBTAP_DIR=/data/local/tmp/a90-acdb-tap`

then `execve()`s the preserved stock HAL path.

## Built private artifacts

Private module output:

`workspace/private/builds/audio/v2487-acdbtap-wrapper-exec-module/`

Public source:

- `workspace/public/src/android/acdb_payload_capture/a90_audio_hal_preload_wrapper_v2487.c`
- `workspace/public/src/scripts/revalidation/native_audio_acdbtap_wrapper_exec_planner_v2487.py`

Artifact metadata:

| artifact | SHA-256 | size | notes |
| --- | --- | ---: | --- |
| wrapper `android.hardware.audio.service` | `cb6d31b7f6763246476f1aa4c638972eb9c5a68975e45c6b97ed101b1254e19a` | 2944 | 32-bit ARM ELF, interpreter `/system/bin/linker` |
| preserved stock HAL | `c57d939fc6eb5c68f81d9d890dabdadb88c9ae10bdc7c9db853fb64e9294da81` | 10424 | copied privately from V2324 vendor dump |
| V2475 `libacdbtap.so` | `7bf64bb04530202a8dc859db0826cd399ff34d51ea4628eb586808de82968be4` | 5864 | copied privately from V2475 build |

The wrapper is freestanding and syscall-only because the private Android clang bundle does
not provide an Android sysroot. It does not include libc headers, does not call `setenv()`,
and does not open `/dev/msm_audio_cal`.

## Safety boundary

The generated module intentionally contains no:

- `service.sh`
- `post-fs-data.sh`
- `system.prop`
- `sepolicy.rule`
- `android.hardware.audio.service.rc`

Command safety passed with no `setenforce 0`, `magisk --install-module`, native
`AUDIO_SET_CALIBRATION`, native speaker playback, or own-process `acdb_loader_init_v4`
fallback tokens.

This unit remains measurement-only. It does not issue native `/dev/msm_audio_cal` ioctls,
does not run native `tinymix`/`tinyplay`, and does not include raw ACDB payload bytes.

## Future live gate

The next live unit must be a wrapper-exec preflight before any playback:

1. install the transient module by direct staged copy;
2. reboot Android for Magisk overlay mount;
3. verify wrapper/original/tap paths and SHA-256;
4. capture `ls -lZ` for all three overlaid paths;
5. restart `android.hardware.audio.service`;
6. verify the new HAL process starts and maps `/vendor/lib/libacdbtap.so`;
7. if linker/SELinux/exec denial appears, capture it and stop.

No AudioTrack stimulus should run until the current HAL PID maps `libacdbtap.so`.

When a full live capture runs, acceptance is the complete ordered set of all
`acdb_ioctl` records with `out_len > 0`, not only `out_len == 4916`. If the live run
ends as `captured-acdbtap-full-outbuf-set-no-4916`, classify it as partial success:
the per-device AFE/ASM/ADM/VOL payloads are still operator-valuable, the run must be
preserved, and it must not count as a dead retry in the fails-twice budget.

## Validation

Commands run:

```bash
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdbtap_wrapper_exec_planner_v2487.py
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_native_audio_acdbtap_wrapper_exec_planner_v2487 -v
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdbtap_wrapper_exec_planner_v2487.py
file workspace/private/builds/audio/v2487-acdbtap-wrapper-exec-module/system/vendor/bin/hw/android.hardware.audio.service
```

Results:

- `py_compile`: passed
- unit tests: 5 passed
- planner: `ok=true`
- wrapper file type: `ELF 32-bit LSB shared object, ARM, dynamically linked, interpreter /system/bin/linker`
