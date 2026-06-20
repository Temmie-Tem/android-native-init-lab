# Native Init V2949 Bad Apple PCM Gain Live Validation

## Summary

- Cycle: `V2949`
- Track: active Video playback pipeline / Bad Apple Player HUD audio volume polish.
- Decision: `v2949-badapple-pcm-gain-live-pass`
- Result: PASS
- Device image: `A90 Linux init 0.10.50 (v2948-badapple-pcm-gain)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2948_badapple_pcm_gain.img`
- Boot SHA256: `29b05291ef638f51a5c1b4abd93e15650180f474890df82b1dd424699c315b5d`
- Rollback precondition: v2321/v2237/v48 images present and SHA-verified before flash.

## Purpose

V2947 proved full-song Bad Apple Player HUD playback with audible PCM, but the operator requested the volume be reduced slightly after full playback looked stable. V2948 adds an attenuation-only PCM-file gain option so volume can be reduced without touching smart-amp gain, boost, PMIC, backlight, or route calibration controls.

## Source Delta Under Test

- New CLI option: `audio play ... --pcm-gain-milli N`.
- Safety model: attenuation-only, `AUDIO_PCM_GAIN_MILLI_MAX=1000`; values above unity are refused.
- PCM-file validation now checks `scaled_peak_abs = ceil(peak_abs * pcm_gain_milli / 1000)` against the existing amplitude cap.
- Playback applies gain to PCM-file chunks before ALSA writes; generated tone playback is unchanged.

## Static Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2948_badapple_pcm_gain.py tests/test_native_audio_pcm_gain_v2948.py`: PASS
- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_badapple_fullsong_pcm64_v2945 tests.test_native_audio_pcm_gain_v2948 -v`: PASS, 9 tests
- V2948 boot build: PASS
- V2948 boot SHA256: `29b05291ef638f51a5c1b4abd93e15650180f474890df82b1dd424699c315b5d`

## Flash / Health

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash result: PASS; boot readback SHA matched `29b05291ef638f51a5c1b4abd93e15650180f474890df82b1dd424699c315b5d`
- Post-flash version: `A90 Linux init 0.10.50 (v2948-badapple-pcm-gain)`
- Pre-play selftest: `pass=12 warn=1 fail=0`
- Final selftest: `pass=12 warn=1 fail=0`
- Final status: V2948 resident, runtime SD writable, transport serial/tcpctl ready.

## Live Command

Audio worker:

```text
audio play internal-speaker-safe --mode listen --duration-ms 232090 --amplitude-milli 150 --pcm-gain-milli 840 --pcm-file /cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le --execute
```

Video HUD:

```text
video demo badapple play --trust-cache --present pageflip --layout player-hud --sync-audio-status /cache/a90-audio-play/status.txt --sync-wait-ms 60000 --sync-start-offset-ms 450
```

## Audio Result

- Worker started: `audio.play.worker.pid=658`
- Gain marker: `audio.play.worker.pcm_gain_milli=840`
- PCM file peak: `audio.play.pcm_file.peak_abs=5809`
- Scaled peak: `audio.play.pcm_file.scaled_peak_abs=4880`
- Peak limit from `--amplitude-milli 150`: `audio.play.pcm_file.peak_limit=4915`
- Cap result: `audio.play.pcm_file.amplitude_within_cap=1`
- Drain: `audio.play.execute.drain.rc=0 errno=0`
- Frames done: `11140320`
- Bytes done: `44561280`
- Worker completion: `audio.play.worker.done=1 rc=0`, `exit_code=0`

## Video / Sync Result

- Cache asset: `badapple-480x360-full-v2903`
- Cache stream SHA: `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- Cache stream size: `150490668`, expected size matched.
- Audio sync ready: `1`, ready elapsed `0ms`
- Audio sync start offset: `450ms`
- Presented frames: `6962`
- Total frames: `6962`
- Dropped frames: `0`
- Elapsed: `232038162932ns`
- Effective FPS: `30003 milli-fps`
- Pageflip events: `6962`
- Beat flash: enabled, table count `388`, active frames `1643`
- Command rc: `0`

## Operator Observation

During the run, the operator reported the HUD remained visible intermittently and audio playback had no abnormal behavior. The final objective evidence confirms the audio worker and video HUD completed the full run cleanly with gain attenuation active.

## Safety

- No smart-amp gain/boost changes.
- No PMIC, regulator, GDSC, GPIO, DSI backlight, or route-expansion writes.
- The only persistent device write in this unit was the checked boot flash to the boot partition.
- Generated boot image and raw run logs remain private/untracked.
