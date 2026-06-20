# Native Init V2938 Audio Audibility Route Diagnosis

## Summary

- Cycle: `V2938`
- Track: active Video playback pipeline / Bad Apple Player HUD audio audibility.
- Result: diagnostic complete; source fix required.
- Device image under test: `A90 Linux init 0.10.45 (v2936-badapple-preview200-audio)`.
- Private evidence: `workspace/private/runs/audio/v2938-audibility-route-snapshot-20260620-092943/live.log`.

## Findings

- Bounded native tone playback completed successfully: `duration_ms=10000`, `bytes_done=1920000`, `done=1`, `rc=0`.
- Post-run `selftest` stayed clean: `fail=0`.
- Active read-only `tinymix --all-values` snapshot during playback showed the core route was applied:
  - `SLIMBUS_0_RX Audio Mixer MultiMedia1` = `On Off`
  - `SLIM RX0 MUX` = `AIF1_PB`
  - `RX INT7_1 MIX1 INP0` = `RX0`
  - `COMP7 Switch` = `On`
  - `Audio Stream 0 App Type Cfg` = `69941 15 48000 2 ...`
- The same active snapshot showed speaker endpoint controls remained off:
  - `SpkrLeft COMP Switch` = `Off`
  - `SpkrLeft BOOST Switch` = `Off`
  - `SpkrLeft VISENSE Switch` = `Off`
  - `SpkrLeft SWR DAC_Port Switch` = `Off`

## Root Cause

Integrated `audio play` still applies and resets only `audio route internal-speaker-safe --layer core`.
That path is enough to move PCM data through ALSA/ADSP, but it leaves the WSA speaker endpoint off.
This explains the operator report that the Bad Apple video was visible while audio was not heard.

## Fix Direction

Add a write-allowed `playback` route layer that includes:

- `core` controls.
- `feedback` controls.
- endpoint controls that are not marked `smart_amp_boost`.

Keep `SpkrLeft BOOST Switch` blocked. Do not add smart-amp gain/boost writes, PMIC/regulator/GPIO writes, or any path outside the existing audio recoverable envelope.

## Safety

- The V2938 diagnostic used only the existing native audio command surface and a read-only mixer snapshot during a bounded 0.2-cap tone.
- No boot image was flashed in this diagnostic step.
- No raw logs are committed; private logs remain under `workspace/private/runs/audio/`.
