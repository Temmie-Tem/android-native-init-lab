# NATIVE_INIT V2378 — Native Speaker Route Recipe Planner

Date: 2026-06-15

## Purpose

Convert the V2377 Android route-delta evidence into a machine-checkable native-init speaker playback recipe and safety plan.

This is host-only. It does not run `tinymix set`, open PCM, write PCM data, or run `tinyplay`.

## Inputs

Private evidence:

```text
workspace/private/runs/audio/v2377-android-route-delta-modern-apk-20260615-042113/
```

Required V2377 evidence verified by the planner:

```text
result_ok=True
rolled_back=True
apk_sha256=fef87886bd1fb5f3dd07b857bbe3c4c00f9046f797ba9c84d48b89dc1d2d13f3
A90_AUDIO_STIMULUS_BEGIN=1
A90_AUDIO_STIMULUS_END=1
A90_AUDIO_STIMULUS_FINISH=1
A90_AUDIO_STIMULUS_ERROR=0
REVIEW_PERMISSIONS=0
AudioTrack delivered 96000 frames
speaker device evidence present
```

Private tinyalsa tools verified:

| Tool | SHA256 |
| --- | --- |
| `tinymix` | `747b19a5a263a3f2f02223ba2bad2aa0e34f9e8a3948093d612d57e3ada15411` |
| `tinyplay` | `03fd8faa9363f97f58a0b094c1504ae4c6f7d8d37f7befd908eaecc6afe81db0` |

## New Planner

Added:

```text
workspace/public/src/scripts/revalidation/native_audio_speaker_route_recipe_v2378.py
```

The planner:

1. Verifies V2377 route-delta evidence and rollback.
2. Parses baseline/active/post `tinymix --all-values`.
3. Confirms exact control names and active values.
4. Emits a future route-apply sequence, reverse reset sequence, and low-amplitude `tinyplay` plan.
5. Rejects unsafe bounds such as amplitude above `0.05`, duration above `1000ms`, or forbidden partition/flash tokens.

Dry-run result:

```text
decision=v2378-native-speaker-route-recipe-ready
ok=True
evidence_ok=True
controls=14
apply_commands=13
reset_commands=12
command_safety.ok=True
```

## Future Route Apply Plan

Future exact-gated native pilot should apply only V2377-observed controls in this order:

| Order | Control | Future active value |
| ---: | --- | --- |
| 1 | `Audio Stream 0 App Type Cfg` | `69941 15 48000 2 ...` |
| 2 | `Playback Channel Map0` | `1 2 0 ...` |
| 3 | `SLIMBUS_0_RX Audio Mixer MultiMedia1` | `On Off` |
| 4 | `SLIM RX0 MUX` | `AIF1_PB` |
| 5 | `RX INT7_1 MIX1 INP0` | `RX0` |
| 6 | `COMP7 Switch` | `On` |
| 7 | `AIF4_VI Mixer SPKR_VI_1` | `On` |
| 8 | `AIF4_VI Mixer SPKR_VI_2` | `On` |
| 9 | `SLIM_4_TX Format` | `PACKED_16B` |
| 10 | `SpkrLeft VISENSE Switch` | `On` |
| 11 | `SpkrLeft COMP Switch` | `On` |
| 12 | `SpkrLeft BOOST Switch` | `On` |
| 13 | `SpkrLeft SWR DAC_Port Switch` | `On` |

`ADSP Path Latency 0` is intentionally classified as observe-only. It is a readback signal, not a route write.

## Future Playback Plan

The future pilot plan is bounded:

```text
tinyplay /cache/a90-audio/v2378-speaker-pilot/pilot_48k_s16le_stereo_0p02_1s.wav -D 0 -d 0
sample_rate=48000
channels=2
format=S16_LE
amplitude=0.02
duration_ms=1000
```

Card/device basis:

- V2377 `/proc/asound/pcm` shows `00-00: MultiMedia1 (*) : playback 1 : capture 1`.
- V2367 read-only inventory proved `tinypcminfo -D 0 -d 0` returns playback/capture caps, including `S16_LE`, `48000Hz`, and stereo-capable channel range.

## Future Reset Plan

Future live runner must reset route switches in reverse order after playback:

1. `SpkrLeft SWR DAC_Port Switch=Off`
2. `SpkrLeft BOOST Switch=Off`
3. `SpkrLeft COMP Switch=Off`
4. `SpkrLeft VISENSE Switch=Off`
5. `SLIM_4_TX Format=UNPACKED`
6. `AIF4_VI Mixer SPKR_VI_2=Off`
7. `AIF4_VI Mixer SPKR_VI_1=Off`
8. `COMP7 Switch=Off`
9. `RX INT7_1 MIX1 INP0=ZERO`
10. `SLIM RX0 MUX=ZERO`
11. `SLIMBUS_0_RX Audio Mixer MultiMedia1=Off Off`
12. `Playback Channel Map0=0 0 ...`

`Audio Stream 0 App Type Cfg` is not included in the mandatory reset sequence because Android left it configured in the post snapshot. A future live runner may add an optional stream-config cleanup only after proving it is safe.

## Future Gate

The generated plan defines the future live approval phrase:

```text
AUD-4-native-speaker-pilot go: one-shot V2377 observed route apply, low-amplitude tinyplay, reverse reset, rollback to V2321
```

Even with overnight preauthorization, the next unit should first implement an exact-gated runner and static tests. The runner must preserve:

- checked-helper boot-only flash path,
- V2321 rollback,
- ADSP boot and `/dev/snd` materialization gates,
- exact route-control presence check before any write,
- one-shot low-amplitude playback,
- reverse reset,
- post-reset `tinymix` verification,
- final `selftest fail=0`.

## Magisk Direction

Magisk is not part of the native-init runtime path: a native speaker pilot must still be
boot-image based, exact-gated, and rollbackable to V2321 without assuming Android services or
Magisk are present.

Keep Magisk as an Android-side support layer, matching the earlier Wi-Fi workflow pattern:

- delivery fallback when `adb install`/`app_process`/framework stimulus delivery is blocked,
- temporary Android-side helper packaging for route capture or additional vendor-log probes,
- boot-time Android stimulus hooks when a future delta needs deterministic timing before manual
  `adb` orchestration is ready,
- private-only artifact staging under `workspace/private/`, never committed as a module zip or
  payload.

Magisk should therefore be documented as a reusable measurement fallback, not as the primary
solution for native playback. The current AUD-4 path should proceed natively unless a new Android
handoff wall appears.

## Validation

Commands run:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_speaker_route_recipe_v2378.py tests/test_native_audio_speaker_route_recipe_v2378.py
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_route_recipe_v2378.py --dry-run
PYTHONPATH=tests python3 -m unittest tests.test_native_audio_speaker_route_recipe_v2378 -v
```

Focused test result:

```text
Ran 5 tests
OK
```

## Decision

`native-speaker-route-recipe-ready`

Next unit: implement the exact-gated native speaker pilot runner as source/build/test only. Do not run live playback until that runner has static safety coverage and the exact AUD-4 gate is used.
