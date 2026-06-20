# Native Init V2940 Bad Apple Playback Route Live Validation

- Date: 2026-06-20
- Track: active Video / Bad Apple Player HUD A/V preview.
- Decision: `v2940-badapple-playback-route-live-pass`
- Resident image: `A90 Linux init 0.10.46 (v2939-badapple-playback-route)`
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v2939_badapple_playback_route.img`
- SHA256: `76764eab1ad6d55401deda7fc7c7cccb15a884a42a99a4e509cf2799a947c69a`

## Purpose

V2937 proved the 300-frame Bad Apple Player HUD preview rendered, but the operator did not hear music. V2938 localized the root cause: `audio play` applied only the core playback path, leaving the non-boost speaker endpoint off. V2939 changed the integrated audio route stage from `core` to `playback`, which includes core + feedback + non-boost endpoint controls while still blocking `SpkrLeft BOOST`.

## Live Validation

1. Flashed V2939 with the checked flash helper.
2. Post-flash health passed:
   - `version`: `A90 Linux init 0.10.46 (v2939-badapple-playback-route)`
   - `selftest`: `pass=12 warn=1 fail=0`
3. Ran a 10 s bounded native tone:
   - `audio chime --execute --amplitude-milli 200 --duration-ms 10000`
   - worker completed `bytes_done=1920000`, `done=1 rc=0`
   - operator physically heard the beep.
4. Captured active mixer state during the tone:
   - `SLIMBUS_0_RX Audio Mixer MultiMedia1`: `On Off`
   - `RX INT7_1 MIX1 INP0`: `RX0`
   - `SLIM RX0 MUX`: `AIF1_PB`
   - `COMP7 Switch`: `On`
   - `AIF4_VI Mixer SPKR_VI_1`: `On`
   - `AIF4_VI Mixer SPKR_VI_2`: `On`
   - `SpkrLeft COMP Switch`: `On`
   - `SpkrLeft VISENSE Switch`: `On`
   - `SpkrLeft SWR DAC_Port Switch`: `On`
   - `SpkrLeft BOOST Switch`: `Off`
5. Ran the Bad Apple A/V preview explicitly:
   - Audio: `audio play internal-speaker-safe --mode listen --duration-ms 10000 --amplitude-milli 200 --pcm-file /cache/a90-runtime/pkg/av/v2933/audio/badapple_preview200_limited.s16le --execute`
   - Video: `video demo badapple play --trust-cache --frames 300 --present pageflip --layout player-hud --sync-audio-status /cache/a90-audio-play/status.txt --sync-wait-ms 10000 --sync-start-offset-ms 450`
   - Video completed `presented=300`, `dropped_frames=0`, `fps_milli=30071`, `present_mode=pageflip`, `layout=player-hud`.
   - Audio worker completed `bytes_done=1920000`, `done=1 rc=0`.
   - Operator physically heard the Bad Apple audio.
6. Post-playback route cleanup and health passed:
   - `SLIMBUS_0_RX Audio Mixer MultiMedia1`: `Off Off`
   - `AIF4_VI Mixer SPKR_VI_1`: `Off`
   - `AIF4_VI Mixer SPKR_VI_2`: `Off`
   - `SpkrLeft COMP Switch`: `Off`
   - `SpkrLeft VISENSE Switch`: `Off`
   - `SpkrLeft SWR DAC_Port Switch`: `Off`
   - `SpkrLeft BOOST Switch`: `Off`
   - `selftest`: `pass=12 warn=1 fail=0`

## Evidence

Private logs:

- `workspace/private/runs/audio/v2940-playback-route-tone-retry-20260620-093910/live.log`
- `workspace/private/runs/video/v2940-badapple-playback-route-av-20260620-094140/live.log`

## Conclusion

`audio play` now applies the correct non-boost speaker playback route. The Bad Apple Player HUD preview is device-proven with synchronized video and audible music under the existing safety cap (`amplitude_milli=200`, no smart-amp boost writes).
