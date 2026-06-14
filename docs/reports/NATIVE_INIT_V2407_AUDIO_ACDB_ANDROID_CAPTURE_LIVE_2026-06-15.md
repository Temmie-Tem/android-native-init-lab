# V2407 — AUD-5A Android/Magisk ACDB capture live result

Scope: exact-gated AUD-5A Android-side ACDB/App Type measurement after the V2406 `/data/local/tmp` artifact-path fix  
Device action: checked Android boot handoff, transient Magisk-root observer, Android framework AudioTrack speaker playback, private artifact pull, cleanup, checked rollback to V2321

## Decision

`aud5a-m0-capture-bounded-native-acdb-candidate-rollback-pass`

V2407 successfully ran the M0 transient Magisk-root measurement path. The run captured Android's speaker playback ACDB/App Type sequence and rolled back to the V2321 native-init checkpoint with `selftest fail=0`.

Private evidence root:

```text
workspace/private/runs/audio/v2397-android-acdb-measurement-20260615-080515
```

## Safety and rollback evidence

- Preflight confirmed rollback images:
  - V2321 SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
  - V2237 SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
  - V48 SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- Dry-run remained live-ready: `future_live_ready=true`, `command_safety_ok=true`, no `/cache/a90-audio-acdb-v2396` in commands or generated module files.
- Live runner decision: `v2397-android-acdb-measurement-captured-rollback-pass`.
- All 26 live steps returned OK; no failed step records.
- `stage-0` now succeeds under `/data/local/tmp/a90-audio-acdb-v2396/artifacts`, proving the V2406 path fix.
- Final device health after rollback:
  - `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
  - `selftest: pass=11 warn=1 fail=0`.

## Android measurement evidence

The AudioTrack stimulus ran and finished normally:

```text
A90_AUDIO_STIMULUS_BEGIN duration_ms=2000 sample_rate=48000 amplitude=0.05 speaker_hint=true
A90_AUDIO_STIMULUS_END frames=96000
A90_AUDIO_STIMULUS_FINISH rc=0
```

Relevant Android logcat edges captured during speaker playback:

```text
audio_hw_primary: select_devices: changing use case deep-buffer-playback output device from(0: , acdb -1) to (2: speaker, acdb 15)
audio_hw_utils: send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000, snd_device_be_idx 2
ACDB-LOADER: ACDB -> send_audio_cal, acdb_id = 15, path = 0, app id = 0x11135, sample rate = 48000, afe_sample_rate = 48000
ACDB-LOADER: ACDB -> AUDIO_SET_AUDPROC_CAL cal_type[11] acdb_id[15] app_type[69941]
ACDB-LOADER: ACDB -> GET_AFE_TOPOLOGY_ID for adcd_id 15, Topology Id 1001025d
ACDB-LOADER: ACDB -> AUDIO_SET_AFE_CAL cal_type[16] acdb_id[15]
```

Tinymix snapshot deltas also show the key App Type and route changes:

| Control | Baseline | Active | Post |
| --- | --- | --- | --- |
| `Audio Stream 0 App Type Cfg` | `0 0 0 0 ...` | `69941 15 48000 2 ...` | `69941 15 48000 2 ...` |
| `SLIMBUS_0_RX Audio Mixer MultiMedia1` | `Off Off` | `On Off` | `Off Off` |
| `RX INT7_1 MIX1 INP0` | `ZERO` | `RX0` | `ZERO` |
| `COMP7 Switch` | `Off` | `On` | `Off` |

## Analyzer correction

The live runner originally attached `post_live_analysis` after rollback but before writing the final `result.json` state to disk. Because the V2399 analyzer reads `result.json` from the run directory, it saw the stale `live-started` state and initially reported `negative-no-calibration` even though the raw logcat contained ACDB/App Type evidence.

V2407 fixes that host-side integration bug by writing the current final `result` before invoking the analyzer. Re-running the analyzer against the finalized run now reports:

```json
{
  "decision": "bounded-native-acdb-candidate",
  "ok": true,
  "reasons": [
    "capture has stimulus, App Type, ACDB/msm_audio_cal, and AFE/ASM/ADM calibration edges"
  ]
}
```

The private `result.json` in the run directory has been updated with the corrected `post_live_analysis` for local continuity. Raw logs remain private and are not committed.

## Magisk direction

M0 succeeded technically and captured the relevant speaker playback ACDB/App Type edge. There is no evidence-based reason to escalate to M1 temporary boot module or M2 vendor wrapper now.

Magisk remains an Android-good measurement capsule only. It is not a native-init runtime dependency.

## Validation

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py tests/test_native_audio_acdb_android_measurement_planner_v2396.py
PYTHONPATH=tests python3 -m unittest tests.test_native_audio_acdb_android_measurement_planner_v2396 -v  # 16 tests
PYTHONPATH=tests python3 -m unittest discover -s tests -v  # 1090 tests
python3 workspace/public/src/scripts/revalidation/a90ctl.py --timeout 30 version
python3 workspace/public/src/scripts/revalidation/a90ctl.py --timeout 30 selftest verbose
```

All validation passed.

## Next step

Design the bounded native ACDB/App Type bootstrap from the observed Android sequence. The minimum target is not another blind AUD-5A rerun; it is a host-only design for native-init to reproduce the small calibration/App Type setup needed before the existing AUD-4 tinyalsa PCM prepare path.

Open questions for the next design unit:

1. Which parts of `send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000` can be reproduced through mixer controls alone?
2. Which ACDB loader operations require `/dev/msm_audio_cal` ioctls, and can they be represented as a bounded static helper without Android HAL state?
3. Is `ACDB -> send_audio_cal, acdb_id=15, path=0, app id=0x11135` enough for the native speaker route, or is the preceding `vi-feedback` calibration also required?
