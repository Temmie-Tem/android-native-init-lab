# NATIVE_INIT V2360 — audio route reconciliation after tinyalsa inventory

Date: 2026-06-15

## Scope

Host-only AUD-3 route analysis after V2359. No bridge command, no flash, no ADSP command, no `/dev/snd` materialization, no `tinymix set`, no PCM open/write, no `tinyplay`, no audio HAL, and no `adsprpc` path.

Inputs:

- V2359 read-only inventory: `workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-014528/`.
- Vendor route files from AUD-0: `workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/etc/`.
- Tinyalsa source staged by V2345: `workspace/private/inputs/external_tools/audio/tinyalsa/e14bf1479ebaaabf60bc4472ce8d304f72f03c32/`.
- Private derived summary: `workspace/private/runs/audio/v2360-route-analysis/route_analysis_summary.json`.

## Result

Decision: `v2360-audio-route-reconciliation-host-only-pass`.

V2359 proves the mixer/PCM control plane is usable, but V2360 shows the first audible playback target is still not ready for an immediate live run. The prior V2342 idea of using `deep-buffer-playback headphones` as the safest first route is electrically low-risk, but it is not a reliable audible-output target on this specific device because Galaxy A90 5G has no 3.5 mm headphone jack. The internal speaker route is the real audible target, but its vendor XML and live kcontrol inventory do not yet reconcile cleanly.

## V2359 control evidence

V2359 `tinymix -D 0` identified:

- mixer card: `sm8150-tavil-snd-card`
- controls reported by tinymix: `3628`
- card 0/device 0 PCM out and PCM in query: `rc=0`

Key live controls relevant to low-risk PCM routing:

| Control | Live type/count | Live value | Vendor route value |
| --- | --- | --- | --- |
| `SLIMBUS_0_RX Audio Mixer MultiMedia1` | `BOOL`, `num=2` | `Off Off` | `1` |
| `SLIMBUS_0_RX Audio Mixer MultiMedia5` | `BOOL`, `num=2` | `Off Off` | `1` |
| `SLIMBUS_0_RX Audio Mixer MultiMedia11` | `BOOL`, `num=2` | `Off Off` | `1` |
| `SLIMBUS_0_RX Audio Mixer MultiMedia16` | `BOOL`, `num=2` | `Off Off` | `1` |
| `HPHL Volume` | `INT`, `num=1` | `20` / range `0->20` | already nonzero |
| `HPHR Volume` | `INT`, `num=1` | `20` / range `0->20` | already nonzero |
| `RX0 Digital Volume` | `INT`, `num=1` | `84` / range `0->124` | already nonzero |
| `RX1 Digital Volume` | `INT`, `num=1` | `84` / range `0->124` | already nonzero |

Tinyalsa `tinymix.c` confirms a single numeric set argument is applied to all values of a multi-value numeric control. Therefore a future route command such as `tinymix -D 0 "SLIMBUS_0_RX Audio Mixer MultiMedia1" 1` would set both boolean values for that `num=2` mixer control. This is a design finding only; V2360 did not run it.

## Headphone route: clean control match, weak physical endpoint

Vendor `mixer_paths_tavil.xml` maps several headphone playback usecases to one front-end mixer control, and every tested control is present in the V2359 live card:

| Route | Vendor control | Live control present |
| --- | --- | --- |
| `deep-buffer-playback headphones` | `SLIMBUS_0_RX Audio Mixer MultiMedia1 = 1` | yes |
| `primary-playback headphones` | `SLIMBUS_0_RX Audio Mixer MultiMedia11 = 1` | yes |
| `low-latency-playback headphones` | `SLIMBUS_0_RX Audio Mixer MultiMedia5 = 1` | yes |
| `mmap-playback headphones` | `SLIMBUS_0_RX Audio Mixer MultiMedia16 = 1` | yes |
| `compress-offload-playback headphones` | `SLIMBUS_0_RX Audio Mixer MultiMedia4 = 1` | yes |

`audio_platform_info.xml` maps `SND_DEVICE_OUT_HEADPHONES` to backend `headphones`, interface `SLIMBUS_0_RX`, while `audio_policy_configuration.xml` allows `primary-out` / `fast` to `Wired Headphone` at `48000` Hz stereo PCM.

However, external hardware references report Galaxy A90 5G has no 3.5 mm audio jack. That makes the analog `SND_DEVICE_OUT_HEADPHONES` route a poor first **audible** proof target. It may still be useful as a low-risk route/PCM smoke test, but it should not be represented as likely to produce sound unless the operator has a proven compatible wired analog endpoint. USB-C digital audio is a separate USB host/device problem and conflicts with the current USB gadget control-channel setup.

## Speaker route: audible target, but not reconciled yet

`audio_platform_info.xml` maps `SND_DEVICE_OUT_SPEAKER` to backend `speaker`, interface `SEC_TDM_RX_0`, and marks speaker bit width as `24`. The live V2359 mixer does expose many `SEC_TDM_RX_* Audio Mixer MultiMedia*` controls.

The vendor `mixer_paths_tavil.xml` speaker route is not yet consistent enough for a safe first live speaker attempt:

- `deep-buffer-playback speaker` sets only `SLIMBUS_0_RX Audio Mixer MultiMedia1 = 1`, the same front-end as the headphone route.
- The actual `speaker` / `spk` device path includes codec/smart-amp controls such as `SLIM_0_RX Channels`, `SpkrLeft COMP Switch`, `SpkrLeft BOOST Switch`, `SpkrLeft VISENSE Switch`, `SpkrLeft SWR DAC_Port Switch`, and `SLIM_0_RX XTLoggingDisable`.
- Those `SpkrLeft*` and `SLIM_0_RX*` controls did not appear in the V2359 tinymix inventory by exact name, while live alternatives such as `SEC_TDM_RX_0 Audio Mixer MultiMedia1`, `WSA_CDC_DMA_RX_0_DL_HL Switch`, `COMP7 Switch`, and `SPKR Left Boost Max State` do exist.

That mismatch means direct speaker playback is not just "set MultiMedia1 and play". It likely needs another reconciliation pass against the stock HAL behavior, SoundWire/WSA naming, or a different vendor route path before speaker writes are justified.

## Proposed next safe unit

Do **not** run live playback next. The next safe unit is host-only AUD-3D design/implementation planning with two explicitly separated branches:

1. **AUD-3D0 route/PCM smoke design** — low-risk but possibly inaudible:
   - target route: `deep-buffer-playback headphones`
   - route command design: `tinymix -D 0 "SLIMBUS_0_RX Audio Mixer MultiMedia1" 1`
   - PCM command design: `tinyplay <low-amplitude 48k stereo 16-bit WAV> -D 0 -d 0 -p 1024 -n 4`
   - cleanup design: set the same mixer control back to `0`
   - expected value: confirms route set + PCM open/write path, not necessarily audible sound.
2. **AUD-3D1 speaker route reconciliation** — required before an audible internal-speaker attempt:
   - compare live `SEC_TDM_RX_*`, `WSA_*`, `COMP*`, and `RX INT7*` controls against vendor HAL strings and route XML,
   - identify the exact speaker front-end/backend control set,
   - keep protected-speaker/smart-amp writes out until names and reset path are explicit.

Any future live unit must be separately exact-gated. Suggested minimum phrase for the low-risk route/PCM smoke, if the operator chooses it later:

```text
AUD-3D0-headphone-route-smoke go: one-shot low-amplitude tinyalsa route/PCM smoke on materialized V2334, route deep-buffer-playback headphones only, no speaker route, no additional mixer writes beyond route on/off, rollback to V2321
```

A real internal-speaker playback phrase should not be accepted until AUD-3D1 resolves the speaker route mismatch.

## Safety outcome

- Host-only analysis.
- No device action.
- No mixer write.
- No PCM open/write.
- No playback.
- Proprietary XML and raw tinymix outputs remain private.

## Validation

- Parsed private `mixer_paths_tavil.xml`, `audio_platform_info.xml`, and `audio_policy_configuration.xml` with Python `xml.etree.ElementTree`: PASS.
- Parsed V2359 private `tinymix` / `tinypcminfo` outputs and generated `workspace/private/runs/audio/v2360-route-analysis/route_analysis_summary.json`: PASS.
- Inspected staged tinyalsa `tinymix.c` and `tinyplay.c` source for set/play command semantics: PASS.
- Web-checked A90 5G physical audio jack availability; sources agree there is no 3.5 mm jack.
- No live device command was run.

## External references

- DeviceSpecifications, Samsung Galaxy A90 5G device specification: https://www.devicespecifications.com/en/model/4c7c51e6
- iFixit, Samsung Galaxy A90 5G repair/spec page: https://www.ifixit.com/Device/Samsung_Galaxy_A90_5G
