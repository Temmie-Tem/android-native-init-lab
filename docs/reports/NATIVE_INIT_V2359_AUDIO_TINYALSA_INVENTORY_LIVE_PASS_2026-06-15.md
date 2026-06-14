# NATIVE_INIT V2359 — AUD-3C tinyalsa read-only inventory pass

Date: 2026-06-15

## Scope

- Unit: exact-gated AUD-3C live retry after V2358.
- Approval phrase used: `AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321`.
- Candidate image: V2334 `0.9.292` (`v2334-audio-snd-nodes-preflight`), SHA256 `53b1130cd912ca4019a3d76835eb721804bae0460b920eb7fdfad5509a2dfcac`.
- Rollback target: V2321 `0.9.285` (`v2321-usb-clean-identity-rodata`), SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Raw private run evidence: `workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-014528/`.

## Result

Decision: `v2349-tinyalsa-inventory-live-pass-before-rollback`.

AUD-3C is complete: the runner booted V2334, accepted one ADSP boot, materialized `/dev/snd`, staged `tinymix` and `tinypcminfo` over the repaired tcpctl/toybox transport, ran read-only inventory commands, then rolled back to V2321.

## Evidence

- Candidate V2334 booted and passed the health gate:
  - `version: 0.9.292 build=v2334-audio-snd-nodes-preflight`
  - candidate `selftest verbose`: `fail=0`
- Token-gated ADSP activation was accepted exactly once:
  - `audio.adsp_boot_once.write=accepted`
  - `audio.status.audio_playback_attempted=0`
- `/dev/snd` materialization reproduced:
  - before materialization: `audio.dev_snd.count=0 control_like=0 pcm_like=0`
  - after materialization: `audio.dev_snd.count=61 control_like=1 pcm_like=59`
- Transfer recovery worked after USB/NCM re-enumeration:
  - initial host NCM and tcpctl probes were not ready,
  - `ncm_host_setup.py setup` repaired the link,
  - host ping to `192.168.7.2` succeeded,
  - tcpctl ping returned `pong` and `OK`.
- Tinyalsa tools staged successfully:
  - `tinymix` installed to `/cache/bin/tinymix` over tcpctl,
  - `tinypcminfo` installed to `/cache/bin/tinypcminfo` over tcpctl.

## Tinyalsa inventory

Read-only commands executed successfully:

| Command | Result | Evidence |
| --- | --- | --- |
| `/cache/bin/tinymix -D 0` | `rc=0` | mixer card name `sm8150-tavil-snd-card`; `Number of controls: 3628` |
| `/cache/bin/tinymix -D 0 --all-values` | `rc=0` | range/value form captured for the same card |
| `/cache/bin/tinypcminfo -D 0 -d 0` | `rc=0` | card 0/device 0 playback and capture caps returned |

`tinypcminfo -D 0 -d 0` reported both PCM out and PCM in capability for device 0:

- formats: `S16_LE`, `S24_LE`, `S32_LE`, `S24_3LE`
- rate range: `8000Hz` to `384000Hz`
- channel range: `1` to `16`
- sample bits: `16` to `32`
- playback period size: `2` to `61440`, period count `2` to `8`
- capture period size: `5` to `61440`, period count `2` to `8`

## Safety outcome

- No `tinyplay` command executed.
- No mixer set/write command executed.
- No PCM playback/write command executed.
- No audio HAL path executed.
- No `adsprpc` path executed.
- Candidate post-inventory `selftest verbose` reported `fail=0`.
- Rollback to V2321 completed.
- Final V2321 health check: `version 0.9.285`, `selftest fail=0`.

## Interpretation

The native-init audio path has advanced past node materialization into successful read-only ALSA userspace introspection. This proves:

1. ADSP/Q6 can be brought up under the V2334 native-init test image.
2. The stock sound card appears as `sm8150-tavil-snd-card`.
3. `/dev/snd/controlC0` and PCM nodes are usable enough for `tinymix`/`tinypcminfo` read-only opens/ioctls.
4. The tcpctl + `/bin/toybox netcat` transfer path is sufficient for staging small static tools after candidate USB re-enumeration.

This does **not** prove playback. The next safe unit is host-only route analysis: correlate the captured `tinymix` control names with the private vendor `mixer_paths_tavil.xml` / audio platform files and design the minimal first playback route. Any future `tinymix set`, PCM open-for-playback, or `tinyplay` remains a fresh operator-gated device step.
