# NATIVE_INIT V2367 — AUD-3C tinyalsa inventory replay

Date: 2026-06-15

## Scope

- Unit: operator-requested AUD-3C replay using the existing exact-gated V2349 runner.
- Approval phrase used: `AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321`.
- Candidate image: V2334 `0.9.292` (`v2334-audio-snd-nodes-preflight`), SHA256 `53b1130cd912ca4019a3d76835eb721804bae0460b920eb7fdfad5509a2dfcac`.
- Rollback target: V2321 `0.9.285` (`v2321-usb-clean-identity-rodata`), SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Raw private run evidence: `workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-025616/`.

## Result

Decision: `v2349-tinyalsa-inventory-live-pass-before-rollback`.

The AUD-3C read-only inventory path reproduced again: V2334 booted, ADSP/card state appeared, `/dev/snd` was materialized, `tinymix` and `tinypcminfo` ran read-only over `tcpctl`, and the device rolled back to V2321 with `selftest fail=0`.

This is a reproducibility replay. It does not change the audio frontier: playback and mixer writes remain unattempted.

## Evidence

- Preflight resident health:
  - V2321 `version: 0.9.285 build=v2321-usb-clean-identity-rodata`
  - `selftest verbose`: `fail=0`
- Candidate materialization:
  - before materialization: `audio.dev_snd.count=0 control_like=0 pcm_like=0`
  - after materialization: `audio.dev_snd.count=61 control_like=1 pcm_like=59`
  - `audio.sound_class.count=128 card_like=1 control_like=1`
- Transfer readiness:
  - initial host NCM/tcpctl probes were not ready,
  - one `ncm_host_setup.py setup` repair ran,
  - selected transport was `tcpctl`.
- Read-only tinyalsa commands:
  - `/cache/bin/tinymix -D 0`: `rc=0`, `3628` controls
  - `/cache/bin/tinymix -D 0 --all-values`: `rc=0`, `3628` controls
  - `/cache/bin/tinypcminfo -D 0 -d 0`: `rc=0`

`tinypcminfo -D 0 -d 0` again reported card 0/device 0 playback and capture capabilities:

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
- Candidate post-inventory `selftest verbose`: `fail=0`.
- Rollback to V2321 completed.
- Final V2321 health check:
  - `version: 0.9.285 build=v2321-usb-clean-identity-rodata`
  - `selftest verbose`: `fail=0`

## Interpretation

AUD-3C remains reproducible and safe as a read-only inventory gate. It proves only that the V2334 native-init test image can bring up enough ADSP/ALSA state for mixer and PCM capability introspection.

It still does not justify native speaker playback. The substantive next frontier remains the Android route-delta path from V2362/V2365/V2366: build/stage the Android framework `AudioTrack` stimulus DEX, then run a fresh exact-gated Android route capture before any native `tinymix set`, PCM playback open/write, or `tinyplay` attempt.

## Validation

- `native_audio_tinyalsa_inventory_live_handoff_v2349.py --dry-run`
- exact-gated live run with rollback to V2321
- final `a90ctl.py version`
- final `a90ctl.py selftest verbose`
