# Native Init V2947 Bad Apple Full-Song PCM64 Live Validation

## Summary

- Cycle: `V2947`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Decision: `v2947-badapple-fullsong-pcm64-amp180-live-pass`
- Result: PASS
- Resident init: `A90 Linux init 0.10.49 (v2945-badapple-fullsong-pcm64)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2945_badapple_fullsong_pcm64.img`
- Boot SHA256: `3d8cfb89906b8d0209751568b13cc21bc97f8bb1e3c123896790d45c91f05848`
- Private run log: `workspace/private/runs/video/v2947-badapple-fullsong-pcm64-amp180-live-20260620-102011/`
- Operator observation: video playback visible and audio listening confirmed.

## Context

V2944 proved the new path-scoped full-song duration policy reached the device, but the full-song worker exited before audio sync became ready. The failure was not the 10 s generic duration gate; it was a 32-bit frame-count overflow in `audio_play_execute_pcm()`:

- V2944 command: `--duration-ms 232090 --amplitude-milli 150`
- Policy markers: `effective_duration_ms=240000`, `duration_policy=badapple-fullsong-pcm`, `duration_within_cap=1`
- Failure: `audio.play.execute.error=bad-pcm-geometry`
- Cleanup: `audio stop ... rc=0`, final `selftest fail=0`

V2945 fixes that by computing long PCM frame geometry with 64-bit arithmetic and preserving the generic profile caps. V2946 then showed the next independent gate: the full-song file peak is higher than a 150 m‰ requested amplitude gate.

- V2946 geometry: `total_frames=11140320`, `total_bytes=44561280`
- V2946 peak check: `peak_abs=5809`, `peak_limit=4915`, `amplitude_within_cap=0`
- Failure: `audio.play.pcm_file.error=amplitude-cap-exceeded`
- Cleanup: `audio stop ... rc=0`, final `selftest fail=0`

V2947 reran the same full-song path at `--amplitude-milli 180`, still below the profile safety cap of 200 m‰ and high enough for the verified PCM peak.

## Static Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2945_badapple_fullsong_pcm64.py tests/test_native_audio_badapple_fullsong_pcm64_v2945.py`
- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_badapple_fullsong_pcm64_v2945 -v`
- V2945 builder completed AArch64 static native-init build, helper build, ramdisk pack, boot image pack, and marker check.

## Flash / Health

- Flash path: checked helper `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
- Rollback preconditions were checked before flash: v2321, v2237, and v48 rollback images were present with expected SHA256 values.
- Flash readback SHA matched `3d8cfb89906b8d0209751568b13cc21bc97f8bb1e3c123896790d45c91f05848`.
- Post-flash version/status health passed on V2945.
- V2947 pre-run `selftest`: `pass=12 warn=1 fail=0`.
- V2947 post-run `selftest`: `pass=12 warn=1 fail=0`.

## V2947 Command

```text
audio play internal-speaker-safe --mode listen --duration-ms 232090 --amplitude-milli 180 --pcm-file /cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le --execute
video demo badapple play --trust-cache --present pageflip --layout player-hud --sync-audio-status /cache/a90-audio-play/status.txt --sync-wait-ms 60000 --sync-start-offset-ms 450
```

## Audio Result

- Policy: `audio.play.cap.duration_policy=badapple-fullsong-pcm`
- Effective duration cap: `240000 ms`
- Requested duration: `232090 ms`
- Requested amplitude: `180 m‰`
- Profile amplitude cap: `200 m‰`
- PCM expected bytes: `44561280`
- PCM actual file size: `44561952`
- PCM peak: `5809`
- Peak limit at 180 m‰: `5898`
- `audio.play.pcm_file.amplitude_within_cap=1`
- `audio.play.pcm_file.validated=1`
- `audio.play.execute.total_frames=11140320`
- `audio.play.execute.total_bytes=44561280`
- `audio.play.execute.drain.rc=0 errno=0`
- `audio.play.execute.frames_done=11140320`
- `audio.play.execute.bytes_done=44561280`
- `audio.play.execute.done=1 chunks=10880 frames=11140320 bytes=44561280`
- `audio.setcal.execute.ok=1`
- `audio.play.integrated.done=1 rc=0`

## Video / HUD Result

- Asset: `badapple-480x360-full-v2903`
- Stream SHA256: `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- Audio SHA256 in beat table: `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`
- `video.stream.audio_sync.ready=1`
- Audio sync ready elapsed: `0 ms`
- Audio sync start offset: `450 ms`
- Audio sync total frames: `11140320`
- Presented frames: `6962`
- Total frames: `6962`
- Dropped frames: `0`
- Flip events: `6962`
- FPS: `30002 mHz`
- Flip delta avg: `33333 us`
- Present path: `kms-dumb-buffer-pageflip`
- Pixel format: `mono1`
- Layout: `player-hud`
- BEAT FLASH active frames: `1643`
- Video command rc: `0`

## Safety / Boundaries

- No boot image embedded the 150 MB frame stream or 44 MB PCM; both stayed in the SD/runtime cache.
- No Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths were added.
- Audio remained within the existing `internal-speaker-safe` profile safety cap.
- `SpkrLeft BOOST Switch` stayed blocked by policy.
- Cleanup route reset completed after the run.

## Conclusion

V2947 satisfies the Bad Apple Player HUD full-song playback checkpoint: the device rendered the full 6962-frame stream with pageflip HUD, BEAT FLASH telemetry, audio-clock sync, zero dropped frames, and completed the bounded speaker PCM worker successfully. The concrete fixes are the path-scoped full-song duration policy and 64-bit PCM frame geometry; the runtime parameter for this PCM is `--amplitude-milli 180`, not 150, because the verified file peak is 5809.
