# NATIVE_INIT_V2461_AUDIO_ACDB_COMPAT_IOCTL_LIVE_CAPTURE_2026-06-15

## Summary

V2461 reran the Android-good AUD-5L M1 hybrid late-observer path with the
V2460 compat-aware helper. The run stayed inside the recoverable envelope:
Android was booted through the checked helper, the temporary Magisk measurement
capsule was removed, rollback to V2321 passed, and a post-run native selftest
reported `fail=0`.

This closes the V2459/V2460 observer gap. The stock audio service does issue
32-bit ARM compat ioctls to `/dev/msm_audio_cal`, and V2461 captured the
fd-matched payload sequence.

## Live Result

- Private run directory: `workspace/private/runs/audio/v2461-acdb-compat-live-20260615-190530/`
- Runner decision: `v2451-acdb-m1-hybrid-late-observer-payload-captured-before-rollback-rollback-pass`
- Runner `ok`: `true`
- Rollback target: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Post-run selftest: `fail=0`
- Temporary module cleanup: passed before rollback
- Raw payload policy: raw `bytes_hex` exists only under `workspace/private`; this report records metadata and hashes only.

## Capture Counters

- Classification: `msm-audio-cal-payload-captured`
- JSONL files: `7`
- `syscall_entry_count`: `45592`
- `syscall_stop_count`: `91120`
- `ioctl_any_entry_count`: `21533`
- fd-matched `/dev/msm_audio_cal` `ioctl_entry`: `28`
- fd-matched `/dev/msm_audio_cal` `ioctl_exit`: `28`
- fd misses: `21505`
- clone events: `24`
- tracee adds: `79`
- helper starts: `5`
- helper errors: `1` (`PTRACE_ATTACH EPERM` for one audioserver instance; the later audio HAL instance was captured)

All 28 fd-matched entries came from the 32-bit compat path:

- ABI: `aarch32`
- syscall number: `54`
- regset length: `72`
- target fd: `/dev/msm_audio_cal`
- return values: all `0`

The request distribution was:

- `0xc00461c8` / `AUDIO_ALLOCATE_CALIBRATION`: `26`
- `0xc00461c9` / `AUDIO_DEALLOCATE_CALIBRATION`: `1`
- `0xc00461cb` / `AUDIO_SET_CALIBRATION`: `1`

The constants map to `CAL_IOCTL_MAGIC 'a'` commands in
`techpack/audio/4.0/include/uapi/linux/msm_audio_calibration.h`:

- `AUDIO_ALLOCATE_CALIBRATION = _IOWR('a', 200, void *)`
- `AUDIO_DEALLOCATE_CALIBRATION = _IOWR('a', 201, void *)`
- `AUDIO_SET_CALIBRATION = _IOWR('a', 203, void *)`

## Payload Header Sequence

The table below decodes only the common public header fields from the first 32
bytes of each captured request buffer:

- `struct audio_cal_header`: `data_size`, `version`, `cal_type`, `cal_type_size`
- `struct audio_cal_type_header`: `version`, `buffer_number`
- `struct audio_cal_data`: `cal_size`, `mem_handle`

No raw payload bytes are included.

| seq | ioctl | cal_type | buffer | cal_size | mem_handle | ret | payload_sha256 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 2 `CVP_VOCPROC_STATIC_CAL_TYPE` | 0 | 0 | 17 | 0 | `75a191f6e05bc87f557e999cf9987e6cd0b816e402fea324c3b8255ceff89518` |
| 2 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 3 `CVP_VOCPROC_DYNAMIC_CAL_TYPE` | 0 | 0 | 18 | 0 | `3e558e40cbf9d35a2eb57b50d892693a385131c970277e1271e01635434dd9de` |
| 3 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 4 `CVS_VOCSTRM_STATIC_CAL_TYPE` | 0 | 0 | 19 | 0 | `1c978a2e523a8c0cb52001bda179dfa10abc94a6fe64ff15b2f9b569d92b57b8` |
| 4 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 5 `CVP_VOCDEV_CFG_CAL_TYPE` | 0 | 0 | 20 | 0 | `5426928a120000b0161f50bc8b9d0228861c7db51cccddc4daa1026f8e986084` |
| 5 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 10 `ADM_CUST_TOPOLOGY_CAL_TYPE` | 0 | 0 | 21 | 0 | `d1e4dd406009d9f9359788f3a33e14143c85d7de4e120a51bc77040b47276312` |
| 6 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 11 `ADM_AUDPROC_CAL_TYPE` | 0 | 0 | 22 | 0 | `612018383e7f597427f888c38742fa846c9ef608992ab88b48830caa65edea24` |
| 7 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 11 `ADM_AUDPROC_CAL_TYPE` | 1 | 0 | 23 | 0 | `46b5cf1a56de73cfcbaf957987721bec208a8188b0a5f0d3ebe718e1712219bc` |
| 8 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 12 `ADM_AUDVOL_CAL_TYPE` | 0 | 0 | 24 | 0 | `81d5032e793e39f96014592b13615b9b347b9ef5a70cf49a2b3b85117c7b2f3b` |
| 9 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 12 `ADM_AUDVOL_CAL_TYPE` | 1 | 0 | 25 | 0 | `fac397074d1a290a2a04e8fe45842c9f1ba211fd8be5b606ca6938094fcdf2c8` |
| 10 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 14 `ASM_CUST_TOPOLOGY_CAL_TYPE` | 0 | 0 | 26 | 0 | `bd2975f42d976800097f440f40bc8e663ef85d09bc260a9c8bfc9307028ce600` |
| 11 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 15 `ASM_AUDSTRM_CAL_TYPE` | 0 | 0 | 27 | 0 | `eaee8b83407d398b88683d0afe848088a9c1a9020bab4c83da7a6c59c9519c98` |
| 12 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 16 `AFE_COMMON_RX_CAL_TYPE` | 0 | 0 | 28 | 0 | `2361ebc0d385bb936bc65d16ba4ea0f1357e53bd5f0e984ac73e4b8804605b9f` |
| 13 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 17 `AFE_COMMON_TX_CAL_TYPE` | 0 | 0 | 29 | 0 | `2d8813cb28ac85ebeebfd112e7c3fed1172daf887f67c7fc2f13b4e35c6bf7fd` |
| 14 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 19 `AFE_AANC_CAL_TYPE` | 0 | 0 | 30 | 0 | `d9eb610c852b3a9c4888be5c3222f69ef5fcb65888f3be731eefd37113221ab8` |
| 15 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 24 `AFE_CUST_TOPOLOGY_CAL_TYPE` | 0 | 0 | 31 | 0 | `9718c8db69774cf6bed06851a197f10c44e6d04b36f1f10187d7d11b6d3ac4aa` |
| 16 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 25 `LSM_CUST_TOPOLOGY_CAL_TYPE` | 0 | 0 | 32 | 0 | `812ffe907f53c1325c64630bac0527c31ac9e9014ab8cad9caa1a9eca6d36e73` |
| 17 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 27 `LSM_CAL_TYPE` | 0 | 0 | 33 | 0 | `d872721c1e48df596cddfdd74b8529bab6c7d74401349519358964552f6e4da1` |
| 18 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 34 `ULP_AFE_CAL_TYPE` | 0 | 0 | 34 | 0 | `bc905bf1c29c81bef77c92572acf232b4514671166ea330ab06c14a475973fb9` |
| 19 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 35 `ULP_LSM_CAL_TYPE` | 0 | 0 | 35 | 0 | `7aaab09cccd549a7752e39e33d201639ca478901b93845d27f89fc3d4cca8eb8` |
| 20 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 37 `AUDIO_CORE_METAINFO_CAL_TYPE` | 0 | 0 | 36 | 0 | `0e8a85e8681cd566332ec9f7d05631009e0a450341923a0e7814d6245468cc36` |
| 21 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 39 `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` | 0 | 0 | 37 | 0 | `a12a96be8179354781ddbe840da502293e8e7ec3a8eb48dc9f38157186dc543f` |
| 22 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 40 `ADM_RTAC_AUDVOL_CAL_TYPE` | 0 | 0 | 38 | 0 | `9fdd12b82dcaaaf3e46a0843157e69d58c694116c60c934b9b7fdd3da3de854e` |
| 23 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 46 `AFE_LSM_TX_CAL_TYPE` | 0 | 0 | 39 | 0 | `fb05a9bd4009751f5edba54d6c63eec60a0508c2c71bdca73c9f651d93b9445e` |
| 24 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 48 `ADM_LSM_AUDPROC_CAL_TYPE` | 0 | 0 | 40 | 0 | `059999b7d0b86b5345c698785bab6b95103737bda4e2dfed081d7c1b361fad93` |
| 25 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 49 `ADM_LSM_AUDPROC_PERSISTENT_CAL_TYPE` | 0 | 0 | 41 | 0 | `699fc87bdce164cb50bfa0db62c0a3d9136581293471decbd5c6fa84672a78d6` |
| 26 | `AUDIO_DEALLOCATE_CALIBRATION` (`0xc00461c9`) | 39 `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` | 0 | 0 | 37 | 0 | `44d33e36f582f665637fd01a363d9d695334cf790c179e54a278d29c3e998212` |
| 27 | `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) | 39 `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` | 0 | 0 | 37 | 0 | `44d33e36f582f665637fd01a363d9d695334cf790c179e54a278d29c3e998212` |
| 28 | `AUDIO_SET_CALIBRATION` (`0xc00461cb`) | 39 `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` | 0 | 4916 | 37 | 0 | `bcee384dc3e65dfb4ceb1e8c7356036fb0b6f5169be8503ce157212f92293ed6` |

## Android-Good Calibration Edge

The same playback window still shows the Android framework/HAL path reaching the
speaker ACDB edge in logcat, including:

- `send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000`
- `ACDB -> send_audio_cal, acdb_id = 15, path = 0, app id = 0x11135, sample rate = 48000`
- `ACDB -> allocate_cal_block: mmap`
- `AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]`

## Interpretation

V2461 proves that the prior zero-payload result was an observer ABI miss. The
V2460 helper saw the stock 32-bit audio service through the ARM compat ioctl
path and captured the `/dev/msm_audio_cal` sequence.

The captured sequence is not a full native replay implementation by itself. It
pins the first concrete `/dev/msm_audio_cal` command/order/hash evidence:

1. many `AUDIO_ALLOCATE_CALIBRATION` calls allocate calibration handles;
2. `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` handle `37` is deallocated and reallocated;
3. `AUDIO_SET_CALIBRATION` then sends `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` with
   `cal_size=4916` and `mem_handle=37`.

Next work should be host-only: decode the private raw buffers into exact
`msm_audio_calibration.h` structures and design a bounded native N3 replay gate.
Do not issue native calibration ioctls yet. Native replay must remain gated
until the decoded buffer ownership, mem-handle lifetime, and cleanup policy are
explicitly documented.

## Validation

Commands/evidence used:

```sh
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py \
    --run-live --materialize-module-template \
    --capture-duration-sec 90 \
    --android-timeout 420 \
    --adb-command-timeout 120 \
    --approval '<AUD-5L phrase>' \
    --out-dir workspace/private/runs/audio/v2461-acdb-compat-live-20260615-190530

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90ctl.py version

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest verbose
```

Post-run native health:

- `version: 0.9.285 build=v2321-usb-clean-identity-rodata`
- `selftest: pass=11 warn=1 fail=0`

Private artifact provenance:

- `result.json` SHA256: `dbba94058a68462236c67f254437abd346b42ff67767412f293f6a61c65c6ae4`
- `stimulus-logcat.stdout.txt` SHA256: `17b319ece555d82d965ca6f121ba421a1046ead784b658b8b19d8c801434eba9`
