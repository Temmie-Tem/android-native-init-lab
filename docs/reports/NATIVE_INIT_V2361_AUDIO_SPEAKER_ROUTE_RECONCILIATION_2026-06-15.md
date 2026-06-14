# NATIVE_INIT V2361 — speaker route reconciliation

Date: 2026-06-15

## Scope

Host-only AUD-3D1 speaker route reconciliation after V2360. No bridge command, no flash, no ADSP command, no `/dev/snd` materialization, no `tinymix set`, no PCM open/write, no `tinyplay`, no audio HAL execution, and no `adsprpc` path.

Inputs:

- V2359 tinyalsa inventory: `workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-014528/`.
- V2324 vendor route/config extract: `workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/`.
- V2321/V2334 stock boot images under `workspace/private/inputs/boot_images/`.
- Private derived evidence: `workspace/private/runs/audio/v2361-speaker-route-reconcile/`.

## Result

Decision: `v2361-speaker-route-still-unresolved-host-only-pass`.

V2361 narrowed the internal speaker path but did not produce a safe live speaker route. The strongest evidence says the live speaker front-end likely belongs to the kernel-exposed `SEC_TDM_RX_0` / `WSA_CDC_DMA_RX_0` path, not the simple `SLIMBUS_0_RX Audio Mixer MultiMedia1` path that the vendor XML uses for `deep-buffer-playback speaker`. Because the exact speaker route still has no trusted on/off/reset sequence, internal speaker playback remains gated off.

## Evidence: platform mapping

`audio_platform_info.xml` maps:

| Device | Backend | Interface / extra |
| --- | --- | --- |
| `SND_DEVICE_OUT_SPEAKER` | `speaker` | `SEC_TDM_RX_0` |
| `SND_DEVICE_OUT_SPEAKER_PROTECTED` | not explicit | `SEC_TDM_RX_0` |
| `SND_DEVICE_OUT_SPEAKER` | n/a | `bit_width=24` |
| `SND_DEVICE_OUT_HEADPHONES` | `headphones` | `SLIMBUS_0_RX` |

That platform map agrees with V2360's concern: headphones are `SLIMBUS_0_RX`, while speaker is `SEC_TDM_RX_0`.

## Evidence: live V2359 controls

The live V2359 card exposes speaker-relevant controls that were not used by the XML `deep-buffer-playback speaker` path:

| Group | Live controls observed |
| --- | ---: |
| `SEC_TDM_RX_0 Audio Mixer MultiMedia*` | `17` controls (`MultiMedia1` through `16`, plus `21`) |
| `WSA` / `WSA_CDC` related controls | `34` controls |
| speaker-named controls | `8` controls |
| `RX INT7` / `COMP7` / codec path controls | `13` controls |

Representative live controls:

- `SEC_TDM_RX_0 Audio Mixer MultiMedia1` — `BOOL num=2`, `Off Off`
- `WSA_CDC_DMA_RX_0_DL_HL Switch` — `BOOL num=1`, `Off`
- `COMP7 Switch` — `BOOL num=1`, `Off`
- `RX INT7_1 MIX1 INP0` — enum currently `ZERO`, valid values include `RX0`
- `RX INT7_1 INTERP` — enum currently `ZERO`, valid value includes `RX INT7_1 MIX1`
- `SPKR Left Boost Max State` / `SPKR Right Boost Max State` — present

These are plausible pieces of an internal speaker path, but they are not enough to define a safe route. The route still needs a minimal set, ordering, and cleanup/reset model.

## Evidence: vendor XML mismatch

`mixer_paths_tavil.xml` contains:

- `deep-buffer-playback speaker` → `SLIMBUS_0_RX Audio Mixer MultiMedia1 = 1`
- `speaker` → includes `spk`
- `spk` → controls such as `SLIM RX0 MUX`, `CDC_IF RX0 MUX`, `SLIM_0_RX Channels`, `RX INT7_1 MIX1 INP0`, `COMP7 Switch`, `SpkrLeft COMP Switch`, `SpkrLeft BOOST Switch`, `SpkrLeft VISENSE Switch`, `SpkrLeft SWR DAC_Port Switch`, and `SLIM_0_RX XTLoggingDisable`

Exact-name comparison against V2359 tinymix shows the `SpkrLeft*` and several `SLIM_0_RX*` XML controls were not exposed by exact name. The stock kernel image does contain related strings (`SpkrLeft`, `SpkrLeft IN`, `SpkrLeft SPKR`, `VISENSE Switch`, `SWR DAC_Port`, `SEC_TDM_RX_0`, `WSA_CDC_DMA_RX_0`, `SEC_TDM_RX_0 Audio Mixer`, and `WSA_CDC_DMA_RX_0 Audio Mixer`), so this is not a total absence of speaker support. It is a mapping problem between vendor XML, kernel kcontrol names, and the live card state.

## Evidence: HAL/config gaps

`audio.primary.msmnile.so` strings confirm Samsung/Qualcomm speaker feature code exists (`spkr_prot`, `external_speaker`, WSA feature strings, and `SND_DEVICE_OUT_SPEAKER*`). It also references `audio_platform_info_wsa.xml`, but no `audio_platform_info_wsa.xml` or `*wsa*.xml` file is present in the V2324 vendor extract or wider private inputs searched in this unit.

That missing sidecar may be harmless if compiled defaults cover WSA routing, but it means the current file set does not provide a complete declarative speaker route.

## Current route candidates

| Candidate | Status | Reason |
| --- | --- | --- |
| `SLIMBUS_0_RX Audio Mixer MultiMedia1` + `spk` XML path | not safe | XML path references controls absent by exact name in live tinymix; platform says speaker backend is `SEC_TDM_RX_0`, not `SLIMBUS_0_RX` |
| `SEC_TDM_RX_0 Audio Mixer MultiMedia1` only | insufficient | Matches platform interface and live control, but does not cover WSA/smart-amp enable, RX INT7 routing, compander, or cleanup |
| `WSA_CDC_DMA_RX_0_DL_HL Switch` + WSA mixers | insufficient | Live controls exist, but directionality and required pairing with SEC_TDM/RX INT7 are not proven |
| Headphone/SLIMBUS route | low-risk but likely inaudible | Clean route match, but A90 5G has no 3.5 mm jack and USB-C audio conflicts with the gadget control setup |

## Recommendation

Do **not** attempt internal speaker playback from the current evidence. The next safe step should be one of:

1. **Host-only Android route-delta design:** plan a bounded rollbackable Android handoff that captures mixer deltas before/during a normal speaker playback event, then roll back to V2321. This is the cleanest way to learn the vendor HAL's actual `SEC_TDM_RX_0` / WSA route without guessing. It must be separately gated because it intentionally plays audio under Android.
2. **Host-only native route-smoke runner prep:** implement a gated low-risk native route/PCM smoke runner for the `deep-buffer-playback headphones` route only, with explicit expectation that it may be inaudible. This would test PCM write mechanics but not prove internal speaker sound.

A direct native internal-speaker exact phrase should not be accepted until a trusted route-delta or equivalent source evidence identifies the exact `SEC_TDM_RX_0` / WSA control sequence and cleanup path.

## Safety outcome

- Host-only analysis.
- No device command.
- No mixer write.
- No PCM open/write.
- No playback.
- Proprietary blobs, strings, XML, and raw tinymix outputs remain private.

## Validation

- Extracted `audio.primary.msmnile.so` strings to `workspace/private/runs/audio/v2361-speaker-route-reconcile/audio.primary.msmnile.strings.txt`: PASS.
- Searched vendor audio libs for `SEC_TDM`, `WSA`, speaker, and XML missing-control strings: PASS.
- Searched stock boot image strings for `SEC_TDM_RX_0`, `WSA_CDC_DMA_RX_0`, `SpkrLeft`, `SWR DAC`, and `sm8150-tavil-snd-card`: PASS.
- Parsed V2359 tinymix output into `workspace/private/runs/audio/v2361-speaker-route-reconcile/live_speaker_control_summary.json`: PASS.
- `git diff --check`: PASS.
