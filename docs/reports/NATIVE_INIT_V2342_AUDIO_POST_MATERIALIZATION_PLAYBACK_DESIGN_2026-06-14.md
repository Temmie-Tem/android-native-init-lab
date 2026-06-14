# Native Init V2342 Audio Post-Materialization Playback Design

## Summary

- Cycle: `V2342`
- Track: audio AUD-3 host-only playback design.
- Decision: `v2342-audio-post-materialization-playback-design-ready`
- Result: PASS for host-only design.
- Device flash: `no`.
- Device action: `none`.
- Private derived evidence: `workspace/private/runs/audio/v2342-playback-host-design/audio_playback_route_summary.json`.

## Reason

The live frontier is still the exact-gated V2334 `/dev/snd` materialization
preflight. Repeating another no-flash readiness check would add little value.
This unit therefore prepares the next playback step *without* bypassing the
materialization gate: if `/dev/snd` materialization succeeds, the project needs a
bounded, reviewable tinyalsa route/playback plan rather than an ad-hoc mixer
experiment.

## Inputs

- V2324 AUD-0 private vendor inventory:
  `workspace/private/runs/audio/v2324-aud0-inventory/`.
- Vendor route files, kept private:
  - `vendor_dump/etc/mixer_paths_tavil.xml`
  - `vendor_dump/etc/mixer_paths_pahu.xml`
  - `vendor_dump/etc/audio_platform_info.xml`
- V2332 live evidence: ALSA card name `sm8150-tavil-snd-card`.
- V2333 materialization design: playback remains out of scope until
  `/dev/snd/controlC0` and a relevant `pcmC*D*p` node exist.
- AOSP tinyalsa primary references:
  - `https://android.googlesource.com/platform/external/tinyalsa/+/ics-mr0/tinyplay.c`
  - `https://android.googlesource.com/platform/external/tinyalsa/+/tools_r22.2/tinymix.c`
  - `https://android.googlesource.com/platform/external/tinyalsa/+/e14bf1479ebaaabf60bc4472ce8d304f72f03c32/Android.bp`

## Host Findings

### 1. The route file should be `mixer_paths_tavil.xml`

The live card is `sm8150-tavil-snd-card`, so `mixer_paths_tavil.xml` is the
primary route file for the next playback design. `mixer_paths_pahu.xml` remains a
reference only.

Private XML summary:

| File | Size | Total `<path>` nodes | Playback/speaker/headphone candidate names |
| --- | ---: | ---: | ---: |
| `mixer_paths_tavil.xml` | `125599` | `1060` | `656` |
| `mixer_paths_pahu.xml` | `98107` | `857` | `572` |

### 2. Headphones are the safer first output than speaker

`audio_platform_info.xml` maps:

- `SND_DEVICE_OUT_HEADPHONES` to backend `headphones`, interface `SLIMBUS_0_RX`.
- `SND_DEVICE_OUT_SPEAKER` to backend `speaker`, interface `SEC_TDM_RX_0`.
- Speaker calibration and protected-speaker routes exist in the vendor data.

The first actual playback attempt should therefore target **wired headphones**
or a dummy load first, not the internal speaker/smart-amp path. This still
advances the GOAL-defined speaker/headphone playback epic while reducing the
risk of unexpected speaker gain, smart-amp/protection interaction, or loud audio.

Candidate `tavil` route controls from private XML:

| Route | Representative direct mixer control |
| --- | --- |
| `deep-buffer-playback headphones` | `SLIMBUS_0_RX Audio Mixer MultiMedia1` |
| `primary-playback headphones` | `SLIMBUS_0_RX Audio Mixer MultiMedia11` |
| `low-latency-playback headphones` | `SLIMBUS_0_RX Audio Mixer MultiMedia5` |

Speaker route names exist too, but should remain **deferred** until a headphone
playback path is proven or the operator explicitly chooses speaker risk.

### 3. Standalone tinyalsa tools are not currently staged

Host search found no committed/private ready-to-run `tinymix`, `tinyplay`,
`tinypcminfo`, or `libtinyalsa` tool bundle in the active workspace. AUD-0 proved
the vendor HAL depends on `libtinyalsa.so`, but that is not the same as having a
known-good standalone test binary with provenance.

Therefore the next playback-capable unit should not assume tools already exist.
It should first pin/build or vendor a tinyalsa tool bundle under `workspace/private/`
and record:

- source provenance and license,
- toolchain and static/dynamic linkage choice,
- `file` output for AArch64,
- exact SHA256,
- non-commit location for binaries.

AOSP tinyalsa confirms the expected shape: `tinymix` opens a mixer card and can
list/detail/set controls; `tinyplay` parses PCM WAV and opens a PCM output device
through tinyalsa before writing buffers.

## Proposed Staging After Materialization

Do **not** skip the current exact-gated materialization preflight. The sequence
below only becomes actionable after V2334 proves `/dev/snd/controlC0` and at
least one playback `pcmC*D*p` node exist.

### AUD-3B — host-only tinyalsa tool provenance/build

- Build or import a tinyalsa tool bundle privately:
  - `tinymix`
  - `tinypcminfo`
  - `tinyplay`
- Prefer a static AArch64 build if practical to avoid native-init shared-library
  setup. If dynamic linkage is used, explicitly stage matching libraries in a
  private runtime dir and document `LD_LIBRARY_PATH`.
- No device action.
- Deliverable: tool manifest with SHA256 and `file` output.

### AUD-3C — operator-gated mixer/PCM inventory only

Fresh approval required. Device action is bounded to:

1. Boot the current audio candidate and pass health checks.
2. Bring ADSP/card up through the existing one-shot path if needed.
3. Materialize `/dev/snd`.
4. Run **read-only** tinyalsa inventory:
   - mixer card open/list only,
   - PCM info only,
   - no mixer set,
   - no PCM write,
   - no playback.

This separates "can tinyalsa see the card and controls?" from "can we safely
route and play audio?"

### AUD-3D — operator-gated first playback

Only if AUD-3C proves the expected controls/PCM devices:

1. Require headphones/dummy load connected, or explicitly confirm speaker risk.
2. Select `mixer_paths_tavil.xml`.
3. Start with the `deep-buffer-playback headphones` route, because it maps to
   the conventional `MultiMedia1` path in the private XML summary.
4. Use a very short, low-amplitude PCM WAV.
5. Stop immediately after one bounded playback attempt and collect state.

Speaker playback should be a separate later gate.

## Current Hard Stop

The immediate next live step remains the already-designed materialization
preflight, not playback:

```text
AUD-3-preflight go: materialize ALSA /dev/snd nodes only on V2334, no open/ioctl/mixer/playback, rollback to V2321
```

## Safety Boundary

- Host-only XML/source analysis.
- No bridge command.
- No flash.
- No ADSP write.
- No `/dev/snd` materialization.
- No ALSA open/ioctl, mixer set, tinyalsa execution, PCM write, HAL, playback, or
  `adsprpc`.
- Proprietary XML contents and binaries remain under `workspace/private/`.

## Validation

- Parsed private `mixer_paths_tavil.xml`, `mixer_paths_pahu.xml`, and
  `audio_platform_info.xml` with Python `xml.etree.ElementTree`: PASS.
- Generated private route summary:
  `workspace/private/runs/audio/v2342-playback-host-design/audio_playback_route_summary.json`.
- Searched active workspace for staged standalone tinyalsa tools: none found.
- `git diff --check`: PASS.
