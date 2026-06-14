# NATIVE_INIT V2395 — Audio ACDB bootstrap discriminator design

## Scope

Host-only design unit after V2394. No flash, Android boot, Magisk module install, ADSP command,
`/dev/snd` open, mixer write, PCM playback, HAL launch, or ACDB ioctl ran in this unit.

V2393 proved the native speaker pilot reaches Q6/ADM but fails at prepare because the DSP-side
calibration/App Type/topology state is missing. V2394 identified the likely owners of that state:
`audio.primary.msmnile.so` and `libacdbloader.so`. V2395 narrows the next step: decide how to
separate a bounded native ACDB bootstrap from the full Android audio HAL service graph.

## External reference check

- Android documents the Audio HAL as the layer connecting framework audio APIs to drivers/hardware;
  its Core HAL is the API AudioFlinger uses for playback and routing:
  <https://source.android.com/docs/core/audio/implement>
- AOSP's older Qualcomm HAL source shows the same architecture pattern: sound devices map to ACDB
  IDs, route enablement applies mixer paths, and HAL init dynamically loads `libacdbloader.so` and
  calls ACDB initialization through `dlsym`:
  <https://android.googlesource.com/platform/hardware/qcom/audio/+/3033743/hal/audio_hw.c>
- Qualcomm's public audio documentation frames the Qualcomm Android audio HAL use-case layer as the
  path that converts HAL use cases into ALSA mixer controls:
  <https://docs.qualcomm.com/doc/80-88500-3/topic/27_Convert_audio_HAL_use_cases_into_ALSA_mixer_controls.html>

These references are not treated as exact source for Samsung's stripped `audio.primary.msmnile.so`;
they support the architectural inference already visible in the device's own binaries.

## Local evidence inspected

Private evidence file generated for this unit:

- `workspace/private/runs/audio/v2395-acdb-hal-analysis/v2395-symbol-evidence.txt`

Public/current inputs:

- `docs/reports/NATIVE_INIT_V2393_AUD4_PREPARE_DSP_CAL_FAILURE_2026-06-15.md`
- `docs/reports/NATIVE_INIT_V2394_AUDIO_ACDB_HAL_MAGISK_DIRECTION_2026-06-15.md`
- `docs/reports/NATIVE_INIT_V2377_ANDROID_ROUTE_DELTA_MODERN_APK_LIVE_2026-06-15.md`
- `docs/reports/NATIVE_INIT_ARCHITECTURE_OPTIONS_AND_TARGET_2026-06-10.md`
- `workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/`

## Symbol-map findings

### HAL path

The device's stripped 32-bit `audio.primary.msmnile.so` still exports enough dynamic symbols to map
the relevant flow. Selected function symbols:

| Function | Address | Size | Role |
|---|---:|---:|---|
| `adev_open_output_stream` | `0x3bf90` | `12560` | Android output stream creation path |
| `start_output_stream` | `0x39588` | `3700` | starts PCM output usecase |
| `select_devices` | `0x351f0` | `6856` | routes active usecases to sound devices |
| `enable_snd_device` | `0x3443c` | `1092` | enables sound device and ACDB-backed path |
| `route_output_stream` | `0x3afe4` | `2520` | output stream routing helper |
| `acdb_init_v2` | `0x50704` | `1464` | local HAL ACDB setup wrapper |
| `platform_get_snd_device_acdb_id` | `0x55518` | `1720` | maps HAL sound device to ACDB ID |
| `platform_get_default_app_type_v2` | `0x5d410` | `112` | default App Type resolver |
| `platform_send_audio_calibration` | `0x5df34` | `2092` | device-level audio calibration sender |
| `platform_send_audio_cal` | `0x6b3f8` | `228` | narrower audio-cal sender |
| `audio_extn_utils_update_stream_app_type_cfg_for_usecase` | `0x83884` | `916` | usecase App Type configuration updater |
| `set_stream_app_type_mixer_ctrl` | `0x83c18` | `436` | writes App Type mixer control |
| `audio_extn_utils_send_app_type_cfg` | `0x842a8` | `3184` | sends App Type config to mixer/kernel |

The HAL relocation table references `audio_route_init`, `audio_route_apply_and_update_path`,
`mixer_open`, `mixer_get_ctl_by_name`, `mixer_ctl_set_value`, `mixer_ctl_set_array`,
`platform_get_snd_device_acdb_id`, `platform_get_default_app_type_v2`,
`set_stream_app_type_mixer_ctrl`, `audio_extn_utils_send_app_type_cfg`,
`audio_extn_utils_send_audio_calibration`, and `platform_send_audio_calibration`.

This is not a single `tinymix` route. It is a HAL-owned sequence: choose sound device, map ACDB ID,
compute App Type/sample/bit width, update mixer App Type control, and send audio calibration.

### ACDB loader path

The 32-bit `libacdbloader.so` exports the relevant calibration API surface:

| Function | Address | Size | Notes |
|---|---:|---:|---|
| `acdb_loader_init_v4` | `0x808d` | `3160` | largest init routine; likely current device path |
| `acdb_loader_send_common_custom_topology` | `0x8cf1` | `2620` | common topology sender |
| `acdb_loader_send_audio_cal_v5` | `0x9d31` | `876` | fuller audio calibration sender |
| `acdb_loader_send_audio_cal_v4` | `0xb551` | `36` | thin wrapper around the current sender family |
| `acdb_loader_send_audio_cal` | `0xb5ad` | `72` | legacy/simple sender |
| `acdb_loader_get_default_app_type` | `0x9841` | `10` | default App Type helper |
| `acdb_loader_send_gain_dep_cal` | `0xeb59` | `268` | gain-dependent calibration |
| `acdb_loader_reload_acdb_files_v2` | `0xec65` | `704` | ACDB reload path |

Its relocations/imports include `acdb_ioctl`, `ioctl`, `__open_2`, `fopen`, `opendir`, `property_get`,
`ion_open`, `ion_alloc_fd`, `pcm_open`, and tinyalsa mixer calls. Strings from V2394 also show
`/dev/msm_audio_cal`, `/vendor/etc/acdbdata`, and `/vendor/etc/audconf/OPEN`.

No matching ACDB loader headers or prototypes exist in the current repo/vendor dump. Therefore a
raw native caller cannot be safely authored from headers alone; either the call ABI must be recovered
from disassembly/trace, or Android must be used to observe the real call sequence.

## ABI/runtime boundary

The ACDB/HAL libraries are 32-bit ARM Android/Bionic shared objects. The native-init project normally
uses static native helpers; the architecture review already rejected generic static `dlopen` plugin
loading. Directly calling `libacdbloader.so` from a normal static AArch64 native-init helper is not a
valid path.

Any native ACDB bootstrap would need one of these runtime models:

1. a 32-bit Android/Bionic helper executed through the Android linker/runtime environment mounted from
   the stock partitions; or
2. a minimal Android-HAL rehost process that uses the vendor linker/library paths; or
3. a full Android-side/Magisk measurement first, then a carefully bounded native implementation only
   if the observed sequence is small and reproducible.

Model 1 or 2 is already close to rehosting Android vendor userspace. It is not equivalent to the
current tinyalsa static-tool route.

## Speaker-specific state

The speaker path evidence is internally consistent:

- `audio_platform_info.xml` maps `SND_DEVICE_OUT_SPEAKER` to `acdb_id=15` and backend
  `SEC_TDM_RX_0`; `audio_platform_info_diff.xml` maps the same speaker family to backend
  `SLIMBUS_0_RX`.
- V2377 Android playback observed `USAGE_MEDIA` AudioTrack to speaker, delivered `96000` frames at
  48 kHz, and produced the active route:
  `MultiMedia1 -> SLIMBUS_0_RX -> SLIM RX0/AIF1_PB -> RX0 -> RX INT7 -> COMP7 -> SpkrLeft / SWR DAC`.
- V2377 also observed persistent `Audio Stream 0 App Type Cfg = 69941 15 48000 2 ...`.
- V2393 native replay applied the observed route controls but still hit `App type not available`,
  `cal_block is NULL`, and `adm_open` `ADSP_EFAILED`.

So the missing piece is not the visible speaker route. It is the hidden ACDB/App Type/topology state
that Android programs before or during the HAL output start.

## Discriminator design

### Branch A — Android/Magisk measurement first

This is the recommended next branch. Magisk remains a measurement/staging layer only.

Goal: capture the real ACDB/App Type sequence while Android's vendor audio HAL performs a known-good
low-amplitude speaker playback.

Minimum measurement plan:

1. Use the checked Android handoff and V2321 rollback machinery already proven by V2377.
2. Package a temporary Magisk module or Android-side root helper that starts after Android's vendor
   audio services are up.
3. Before playback, snapshot:
   - `getprop` audio-related keys,
   - `ps -A` and `/proc/<audio-hal-pid>/maps` for `android.hardware.audio.service`,
   - `/dev/msm_audio_cal`, `/dev/ion`, `/dev/snd/*`, and relevant service state,
   - `tinymix -D 0 --all-values`, `/proc/asound`, and dmesg tail.
4. During one bounded low-amplitude framework `AudioTrack` playback, capture:
   - `logcat -b all` filtered for `ACDB`, `acdb`, `audio_hw`, `platform`, `adm`, `afe`, `q6asm`,
     `app_type`, `AudioFlinger`, and the stimulus markers,
   - dmesg tail around `send_afe_cal`, `q6asm_send_cal`, `adm_open`, and App Type programming,
   - active `tinymix -D 0 --all-values`.
5. After playback, snapshot the same state and rollback to V2321.

Magisk module direction, matching the earlier Wi-Fi-style handoff pattern:

- build the module zip and any scripts under `workspace/private/` only;
- install it only inside the rollbackable Android handoff window, never in native init;
- use `service.sh` or a root helper as a late-boot observer after `sys.boot_completed=1` and
  `android.hardware.audio.service` is visible;
- keep payloads measurement-only: log capture, state snapshots, optional stimulus launch, and
  optional bounded HAL syscall observation;
- forbid persistent vendor/system partition writes, broad service mutation, audio policy changes,
  mixer writes outside the existing bounded route snapshot plan, and any native boot dependency on
  the module;
- uninstall or leave the module behind only on the disposable Android side of the handoff, then
  rollback to V2321 so the resident native baseline is clean.

This makes Magisk a delivery/observability tool, not an audio solution. The native-init path still
has to be boot-image based, exact-gated, and able to pass `selftest` after rollback without Android
services.

Optional escalation, only if logs remain insufficient: one bounded root `strace`/ptrace window on the
HAL service for `openat`/`ioctl` around `/dev/msm_audio_cal`. This is not the default because ptrace
can perturb audio timing.

Pass condition for Branch A: identify a small, reproducible sequence of ACDB init/send calls,
required files/properties/devnodes, and mixer App Type writes that can be translated into a native
bootstrap attempt.

Fail condition for Branch A: Android evidence shows the sequence depends on broad HAL service state,
HIDL/Binder service registration, speaker-protection daemons, adsprpc/audio-pd services, or opaque
multi-threaded HAL state that cannot be bounded to a small native probe.

### Branch B — native ACDB bootstrap probe

Do **not** implement this before Branch A unless static analysis recovers exact call ABI and sequence.

A future native bootstrap, if justified, should be staged as a private helper and gated separately
from AUD-4 playback. Its first live action should be calibration-only, not playback:

1. Boot V2334-style ADSP + `/dev/snd` materialization.
2. Materialize only required devnodes such as `/dev/msm_audio_cal`, `/dev/ion`, and `/dev/snd/*`.
3. Prepare read-only vendor paths for `/vendor/etc/acdbdata`, `/vendor/etc/audconf/OPEN`, and platform
   XML, without writing vendor partitions.
4. Use an Android/Bionic-compatible helper if vendor shared libraries are called.
5. Run one bounded ACDB/App Type initialization sequence for `speaker/acdb_id=15/app_type=69941/rate=48000`.
6. Capture dmesg and mixer state.
7. Stop before `SNDRV_PCM_IOCTL_PREPARE` or playback unless calibration evidence is positive.

Hard stops for Branch B:

- no call-audio or `q6voice`,
- no broad HAL service graph launch as a side effect,
- no unbounded Android service bring-up inside native init,
- no native `tinyplay` retry until ACDB/App Type evidence changes,
- no committed proprietary blobs or helper binaries.

### Branch C — classify native tinyalsa-direct as HAL-dependent

If Branch A shows that ACDB/App Type initialization requires the full Android HAL/HwBinder/service
context, classify the current tinyalsa-direct speaker path as likely non-viable in native init scope.
That would not mean audio is impossible forever; it means this epic should stop trying blind route
writes and either:

- accept Android/HAL-dependent audio as out of native-init scope, or
- explicitly re-charter a much larger Android vendor-service rehost effort.

## Recommended next unit

V2396 should implement the Branch-A host-only plan as a dry-run-only Android/Magisk ACDB measurement
planner. It should not run Android or install a module yet. The planner should:

- reuse the checked Android handoff and V2321 rollback model,
- emit exact artifacts to stage under `workspace/private`,
- define an exact future approval phrase,
- capture only logs/snapshots unless explicitly escalated,
- redact identifiers and keep all raw Android logs private,
- report whether the planned capture can prove or falsify a bounded native ACDB bootstrap.

## Validation

- Host-only `readelf`, `strings`, XML/report grep, and web primary-source review.
- No device action ran.
- No code changed.
- `git diff --check` required before commit.
