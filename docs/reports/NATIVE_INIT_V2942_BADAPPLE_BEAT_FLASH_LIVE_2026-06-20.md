# Native Init V2942 Bad Apple Beat Flash Live Validation

- Date: 2026-06-20
- Track: active Video / Bad Apple Player HUD.
- Decision: `v2942-badapple-beat-flash-live-pass`
- Resident image: `A90 Linux init 0.10.47 (v2941-badapple-beat-flash)`
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v2941_badapple_beat_flash.img`
- SHA256: `b06f950a3e8f4b78d9a41c1d5291362523bd2337e50d6108d824a0a690cab228`

## Purpose

The Bad Apple Player HUD still showed `BEAT FLASH: ... pending` after V2940. V2941 adds a generated onset timestamp table derived from the private V2903 Bad Apple PCM render and drives the Player HUD border/text from the audio clock instead of a synthetic timer.

## Implementation Under Test

- Public generator: `workspace/public/src/scripts/revalidation/generate_badapple_beat_table_v2941.py`
- Generated table: `workspace/public/src/native-init/v319/a90_badapple_beat_table.h`
- Source audio SHA marker: `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`
- Onset source id: `badapple-v2903-energy-onsets-v2941`
- Beat window: `70 ms`
- Table count: `388`

The raw PCM remains private and uncommitted.

## Live Validation

1. Built V2941 and flashed it with the checked helper.
2. Post-flash health passed:
   - `version`: `A90 Linux init 0.10.47 (v2941-badapple-beat-flash)`
   - `selftest`: `pass=12 warn=1 fail=0`
3. Ran the bounded 10 s Bad Apple A/V preview:
   - Audio: `audio play internal-speaker-safe --mode listen --duration-ms 10000 --amplitude-milli 200 --pcm-file /cache/a90-runtime/pkg/av/v2933/audio/badapple_preview200_limited.s16le --execute`
   - Video: `video demo badapple play --trust-cache --frames 300 --present pageflip --layout player-hud --sync-audio-status /cache/a90-audio-play/status.txt --sync-wait-ms 10000 --sync-start-offset-ms 450`
4. Video result:
   - `video.stream.presented=300`
   - `video.stream.frames_requested=300`
   - `video.stream.dropped_frames=0`
   - `video.stream.fps_milli=30091`
   - `video.stream.flip_delta_avg_us=33335`
   - `video.stream.audio_sync.first_presented_frame=0`
   - `video.stream.audio_sync.initial_drop_late_ns=0`
5. Beat flash result:
   - `video.stream.beat_flash.enabled=1`
   - `video.stream.beat_flash.source=badapple-v2903-energy-onsets-v2941`
   - `video.stream.beat_flash.table_count=388`
   - `video.stream.beat_flash.window_ms=70`
   - `video.stream.beat_flash.active_frames=102`
   - `video.stream.beat_flash.first_frame=39`
   - `video.stream.beat_flash.last_frame=297`
6. Audio worker completed:
   - `audio.play.worker.bytes_done=1920000`
   - `audio.play.worker.done=1 rc=0`
   - Operator physically confirmed audible Bad Apple audio during the same video playback.
7. Post-run health passed:
   - `selftest`: `pass=12 warn=1 fail=0`

## Evidence

Private log:

- `workspace/private/runs/video/v2942-badapple-beat-flash-live-20260620-095450/live.log`

## Notes

- The first `stophud` preflight command lost an `A90P1 END` marker, but the subsequent `selftest`, audio launch, video run, audio status, and final `selftest` all returned normal protocol markers. This did not affect the A/V validation.
- This unit advances Bad Apple DoD item 4 from a pending label to a real audio-clock-driven BEAT FLASH surface for the preview path. Remaining full-demo work still includes full-length 232 s playback acceptance and any final visual/operator confirmation of the beat pulse.

## Safety

- Only the boot partition was flashed, through `native_init_flash.py`.
- No raw audio/video payloads, boot images, private logs, credentials, or device identifiers are committed.
- No Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or smart-amp boost write path was used.
- Audio stayed within the existing cap: `amplitude_milli=200`; `SpkrLeft BOOST` remains blocked by route policy.
