# Native Init V3054 DOOMGENERIC Audio Co-run Live Validation

## Summary

- Cycle: `V3054`
- Track: active Video playback / DOOM capstone.
- Candidate flashed: `V3053`
- Result: PASS
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3053_doomgeneric_audio_corun.img`
- Boot SHA256: `dc863e16cd30852894a9232b1f8630a619e673bf49fb819b82a2743542733b71`
- Installed init: `A90 Linux init 0.10.85 (v3053-doomgeneric-audio-corun)`

## Flash Gate

- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img`: present, SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: present, SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback `boot_linux_v48.img`: present
- Recovery/TWRP: present under `workspace/private/inputs/firmware/twrp/`
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash mode: `--from-native`
- Readback SHA256: `dc863e16cd30852894a9232b1f8630a619e673bf49fb819b82a2743542733b71`

## Live Validation

- Pre-flash health on V3051: `version` OK, `status` OK, `selftest verbose` fail=`0`
- V3053 post-flash helper verification: `version/status` OK
- V3053 explicit health: `selftest verbose` pass=`12` warn=`1` fail=`0`
- `video demo doom status`: PASS
  - `video.demo.engine.bridge=v3053-doomgeneric-audio-corun`
  - `video.demo.sound.active=native-audio-corun-tone-v3053`
  - `video.demo.doom.audio_corun.enabled=1`
  - `video.demo.asset.wad.present=1`
- `video demo doom loop-start 0 --wad runtime-private --sha256 EXPECTED`: PASS
  - `video.demo.doom.loop_start.active=1`
  - `video.demo.doom.loop_start.continuous=1`
  - `video.demo.doom.audio.corun=1`
  - `video.demo.doom.audio.real_doom_sfx=0`
  - `video.demo.doom.audio.start.rc=0`
  - `audio.play.worker.started=1`
- `audio play-status`: PASS
  - Worker entered listen path with `total_frames=480000`, `total_bytes=1920000`
  - Completion observed after stop/status: `audio.play.worker.done=1 rc=0`
- `video demo doom loop-status`: PASS while active and PASS after stop
- `video demo doom loop-stop`: PASS
  - `audio.stop.worker.tracked_pid` present
  - `audio.stop.playback_stop_attempted=1`
  - `audio.stop.worker.stop_rc=0`
  - `audio.stop.route_reset_rc=0`
  - `video.demo.doom.audio.stop.rc=0`
  - `video.demo.doom.clear.rc=0`
- Final health: `version` OK, `selftest verbose` fail=`0`, `loop_status.active=0`

## Notes

- This unit proves native speaker output can co-run with the continuous DOOM presenter and can be stopped through the tracked async audio worker path.
- This is not a real DOOM SFX/music backend yet. The private DOOM engine still uses `-nosound -nomusic`; V3053 deliberately labels the audio as `native-audio-corun-tone-v3053`.
- One initial flash invocation without `--from-native` timed out while waiting for recovery ADB before any boot write evidence. The device remained on V3051 and was rechecked before the successful checked-helper flash.
- Serial partial-input behavior was observed once after post-flash health and once as a one-character command typo under slow input; both were recovered with prompt realignment and single-command retries.

## Next Unit

- Run ID: `V3055`
- Scope: decide between real DOOM SFX backend work (`i_sound`/ALSA mixer integration) and a more demo-friendly bounded PCM/music co-run asset under the existing native audio worker.
