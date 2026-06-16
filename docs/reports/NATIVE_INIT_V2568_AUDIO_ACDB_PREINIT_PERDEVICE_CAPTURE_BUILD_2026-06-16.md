# NATIVE_INIT V2568 — ACDB pre-init-tail per-device capture build

Date: 2026-06-16

## Scope

Host-only implementation of the next ACDB own-process capture route. No Android boot, device
flash, native replay, speaker write, or live ACDB execution was performed.

## Why This Is Not A Plain Post-Init Arm Rerun

The operator handover's safe principle is correct: the `acdb_ioctl` dumper must not perform
file I/O/hash/dump work during early init calls, because V2538 hung at
`ACDB_CMD_INITIALIZE_V2` before any useful events.

The literal "arm after `acdb_loader_init_v3()` returns" route is already covered and is too
late for this binary:

- V2562 implemented manual post-init arm and proved `init_v3()` enters common topology before
  returning.
- V2563 implemented target-only post-`INITIALIZE_V2` capture and successfully banked the real
  4916-byte topology payload before `init_v3()` returned.
- V2567 localized the remaining crash to the `acdb_loader_init_v4()` tail at `pc=0x8b30`,
  before the helper can reach a post-`init_v3()` `send_audio_cal_v5()` call.

Therefore V2568 keeps the useful gating property but moves the per-device attempt into the
only live window that exists: inside the common-topology call, before returning to the known
crashing init tail.

## Implementation

New public source:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_init_drive_exec_linked_v2568.c`
  - Minimal ARM32 helper.
  - Calls `acdb_loader_init_v3("/vendor/etc/audconf/OPEN", "/data/local/tmp/a90-acdb-ownget/delta", 0)`.
  - Does not open `/dev/msm_audio_cal`, issue ioctls, or touch speaker/PCM state.
- `workspace/public/src/android/acdb_payload_capture/libacdb_preinit_perdevice_v2568.c`
  - Exports `acdb_loader_send_common_custom_topology()`.
  - Calls the real common-topology function first, preserving the real topology GET capture.
  - Resolves `acdb_loader_is_initialized`, derives the loaded `libacdbloader.so` base, and patches
    the known init flag at offset `0x18a9c`.
  - Calls `acdb_loader_send_audio_cal_v5(15, 0, 0x11135, 48000, 48000, 0, 1)` while the ACDB tap is
    armed.
  - Exits the process before returning to the `acdb_loader_init_v4()` tail.
- `workspace/public/src/scripts/revalidation/build_android_acdb_preinit_perdevice_capture_v2568.py`
  - Builds a private helper and a single private combined preload.
  - Compiles `libacdbtap_v2475.c` with:
    - `A90_ACDBTAP_ARMED_CAPTURE=1`
    - `A90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=1`
    - `A90_ACDBTAP_CUSTOM_TOPOLOGY_ONLY=0`
    - `A90_ACDBTAP_EXIT_ON_TARGET=0`
  - Links the ioctl interposer that fake-successes `AUDIO_ALLOCATE_CALIBRATION`,
    `AUDIO_DEALLOCATE_CALIBRATION`, and `AUDIO_SET_CALIBRATION` when
    `A90_ACDB_FAKE_ALLOCATE=1`.

## Measurement Boundary

This remains a capture-only build:

- no native ACDB replay,
- no real `AUDIO_SET_CALIBRATION` in fake mode,
- no speaker write,
- no PCM open/write,
- no Magisk persistent module,
- raw ACDB records remain private under `workspace/private/`.

Future live success must still require `ret==0` and non-all-zero raw buffers. Requested
`out_len` alone is not success.

## Private Build Output

Build root:

```text
workspace/private/builds/audio/v2568-acdb-preinit-perdevice-capture-host-only/
```

Private artifacts:

```text
workspace/private/builds/audio/v2568-acdb-preinit-perdevice-capture-host-only/bin/a90_acdb_preinit_perdevice_exec_linked_v2568
workspace/private/builds/audio/v2568-acdb-preinit-perdevice-capture-host-only/bin/liba90_acdb_preinit_perdevice_capture_v2568.so
```

SHA-256:

```text
a90_acdb_preinit_perdevice_exec_linked_v2568
  ee6f66ccbf35bbf5c01aa2f56d8fbc082a3bbd8778a57dca44f3ff8ba08a58a0

liba90_acdb_preinit_perdevice_capture_v2568.so
  469f92b966992e8d5bb39aa6a5ebe621b84df8ce956cd6d2031c47a242d6ecdd
```

## Validation

Commands run:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_preinit_perdevice_capture_v2568.py
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/build_android_acdb_preinit_perdevice_capture_v2568.py --build \
  --build-root workspace/private/builds/audio/v2568-acdb-preinit-perdevice-capture-host-only \
  --manifest workspace/private/builds/audio/v2568-acdb-preinit-perdevice-capture-host-only/manifest.json
```

Build manifest result:

```text
ok=true
source required_ok=true
source prohibited_ok=true
vendor required_for_v2568_ok=true
helper ok=true
preload ok=true
```

Readelf/file checks confirmed:

- helper is ARM32 PIE and imports `acdb_loader_init_v3`;
- preload exports `acdb_ioctl`, `ioctl`, `a90_arm_capture`, and
  `acdb_loader_send_common_custom_topology`;
- preload SONAME is `liba90_acdb_preinit_perdevice_capture_v2568.so`;
- `libacdbloader.so` exports the required `acdb_loader_init_v3`,
  `acdb_loader_is_initialized`, `acdb_loader_send_common_custom_topology`, and
  `acdb_loader_send_audio_cal_v5` symbols.

## Next Gate

A future live run must be exact-gated separately. The expected live decision matrix is:

- `topology+per-device-records`: keep the complete ordered out-buffer set and hand to the operator.
- `topology-only`: useful partial success; per-device call did not emit GETs or failed after topology.
- `flag-patch-or-send-missing`: host-side loader-symbol/offset assumption failed; stop and analyze.
- crash before pulled artifacts or rollback failure: follow the V2321 rollback envelope and stop.

Do not advance to native ACDB replay from this build alone.
