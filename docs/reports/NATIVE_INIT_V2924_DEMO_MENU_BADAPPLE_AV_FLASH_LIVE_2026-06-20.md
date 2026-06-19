# Native Init V2924 DEMO Bad Apple A/V Flash Live Validation

## Summary

- Cycle: `V2924`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Decision: `v2924-demo-menu-badapple-av-flash-live-pass`
- Result: PASS
- Device action: flashed V2923 boot artifact through the checked helper; current resident image matches the expected V2923 identity and SHA.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2923_demo_menu_badapple_av.img`
- Boot SHA256: `212846f44bb707f0acb95a4c552753389e7f7588c3157009eca1c2b3008e3fa3`
- Init: `A90 Linux init 0.10.40 (v2923-demo-menu-badapple-av)`
- Rollback target retained: `v2321-usb-clean-identity-rodata`

## Flash Gate Evidence

- Rollback images verified before the flash:
  - `v2321`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `v2237`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `v48`: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash mode: `--from-native`, protocol verify `cmdv1`
- Flash result:
  - Local boot marker and SHA matched.
  - Recovery handoff succeeded.
  - Recovery-side remote SHA matched.
  - Boot partition write completed.
  - Boot block readback prefix SHA matched.
  - Post-boot version verification matched `A90 Linux init 0.10.40 (v2923-demo-menu-badapple-av)`.

## Health Check

- Bridge: running on `127.0.0.1:54321`, selected serial `/dev/ttyACM0` through `A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00`.
- `version`: `A90 Linux init 0.10.40 (v2923-demo-menu-badapple-av)`
- `status`: `selftest pass=12 warn=1 fail=0`; SD runtime mounted read-write; display `1080x2400`; transport serial ready.
- `selftest verbose`: `pass=12 warn=1 fail=0`; audio row remains bounded with `cap=200`, `boost=blocked`, `sp=unverified`; USB ACM control present.

## Runtime Asset Check

- Bad Apple PCM path: `/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le`
- Expected SHA256: `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`
- Device SHA256: matched.
- Full video stream remains SD-cache/private and is not bundled into the boot image.

## A/V Player HUD Validation

Two serial-driven checks were used because the menu handler starts audio and video from native C, while long serial commands add host typing delay before the video command reaches PID1.

### Slow Serial Caveat

- Audio command returned `rc=0` and started worker PID `624`.
- Video command returned `rc=0` with sync enabled, but command-entry delay made the audio anchor stale:
  - `video.stream.audio_sync.anchor_age_ns=3846744842`
  - `video.stream.presented=1`
  - `video.stream.dropped_frames=119`
  - `video.stream.audio_sync.first_presented_frame=119`
- Interpretation: the player correctly skipped late frames against the audio clock; this is a serial-command latency artifact, not a rendering failure.

### Normal Serial A/V Run

- Audio command returned `rc=0` and started worker PID `652`.
- Video command returned `rc=0` with Player HUD sync enabled:
  - `video.stream.audio_sync.ready=1`
  - `video.stream.audio_sync.anchor_age_ns=396841667`
  - `video.stream.audio_sync.sample_rate=48000`
  - `video.stream.audio_sync.total_frames=192000`
  - `video.stream.audio_sync.expected_duration_ns=4000000000`
  - `video.stream.presented=98`
  - `video.stream.dropped_frames=22`
  - `video.stream.layout=player-hud`
  - `video.stream.audio_sync.first_presented_frame=16`
- Audio status after completion:
  - `audio.play.worker.profile=internal-speaker-safe`
  - `audio.play.worker.mode=listen`
  - `audio.play.worker.amplitude_milli=150`
  - `audio.play.worker.duration_ms=4000`
  - `audio.play.worker.pcm_file=/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le`
  - `audio.play.worker.listen_begin_ns=74452905647`
  - `audio.play.worker.listen_end_ns=80491166062`
  - `audio.play.worker.frames_done=192000`
  - `audio.play.worker.bytes_done=768000`
  - `audio.play.worker.done=1 rc=0`
  - `audio.play.worker.exit_code=0`
- Final `selftest verbose`: `pass=12 warn=1 fail=0`.

## Scope Notes

- The V2923 boot image wires `DEMO > Bad Apple` to the bounded A/V Player HUD preview: 120 video frames, 4 s PCM-file audio, amplitude `150` milli, sync through `/cache/a90-audio-play/status.txt`, and menu restore.
- The direct serial A/V run validates the same native `audio play` and `video demo badapple play` subcommands used by the menu launcher, but it is not a physical keypress selection proof.
- Exact menu keypress validation remains optional follow-up; the code path avoids the serial typing delay because the menu handler invokes the native commands in-process.

## Safety

- No forbidden partitions touched; only the boot partition was flashed via the checked helper.
- No Wi-Fi scan/connect/DHCP/ping.
- No raw DSI, Venus, GPU, backlight, PMIC, regulator, GDSC, GPIO, or telemetry write paths.
- Audio stayed within the existing internal-speaker-safe path and amplitude cap.
- Raw streams, boot images, and private logs remain untracked under `workspace/private/`.
