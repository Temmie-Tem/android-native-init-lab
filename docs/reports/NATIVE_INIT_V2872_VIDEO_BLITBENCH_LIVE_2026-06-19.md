# Native Init V2872 Video Blitbench Live Validation

## Summary

- Cycle: `V2872`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2872-video-blitbench-live-pass`
- Result: PASS
- Candidate: `A90 Linux init 0.10.22 (v2871-video-blitbench)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2871_video_blitbench.img`
- Candidate SHA256: `2693a1bde100c9469615203a96f8e8aeaabc8bb4f701f7f0ea461b61420d925c`
- Rollback target: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/video/v2872-video-blitbench-live-20260619-192435`

## Flash / Health

- Preflight rollback images were present and matched the pinned `v2321`, `v2237`, and `v48` rollback/fallback checksums.
- Candidate flash used only `workspace/public/src/scripts/revalidation/native_init_flash.py` with `--from-native` and pinned candidate SHA.
- Candidate boot verification passed through cmdv1 `version` and `status`.
- Candidate `selftest verbose`: `pass=12 warn=1 fail=0`.
- Candidate post-benchmark `selftest verbose`: `pass=12 warn=1 fail=0`.
- Checked rollback to `v2321` used the same flash helper with pinned rollback SHA and readback SHA match.
- Final rollback `selftest verbose`: `pass=11 warn=1 fail=0`.

## Video Status Evidence

- `video.status.kms.initialized=1`
- `video.status.kms.size=1080x2400`
- `video.status.kms.connector=28`
- `video.status.kms.encoder=27`
- `video.status.kms.crtc=133`
- `video.status.kms.fb=208`
- `video.status.kms.current_buffer=1`
- `video.status.kms.stride=4352`
- `video.status.kms.map_size=10444800`
- `video.status.kms.pixel_format=xbgr8888`
- `video.status.next_blitbench=video blitbench [frames<=240]`

## Blitbench Evidence

Command: `video blitbench 60`

- `video.blitbench.presented=60`
- `video.blitbench.frames=60`
- `video.blitbench.bytes=622080000`
- `video.blitbench.elapsed_ns=986425468`
- `video.blitbench.fps_milli=60825` (`60.825 fps`)
- `video.blitbench.mbps_milli=630640` (`630.640 MB/s` decimal)
- `video.blitbench.width=1080`
- `video.blitbench.height=2400`
- `video.blitbench.stride=4352`
- `video.blitbench.frame_bytes=10368000`
- `video.blitbench.pixel_format=xbgr8888`
- `video.blitbench.path=kms-dumb-buffer`
- cmdv1 completion: `rc=0`, `status=ok`, `duration_ms=1015`.

## Interpretation

`v2872-video-blitbench-live-pass`: the V2871 full-frame KMS memcpy benchmark is device-proven. The current no-clear row-copy plus `SETCRTC` path presents 60 full 1080x2400 XBGR8888 frames in about 0.986 s, enough to exceed a 30 fps playback target under this synthetic benchmark. The next playback units can move from synthetic copy measurement to a private compact frame-stream format and later A/V sync.

The result does not yet prove long-video streaming from storage, vblank/page-flip timing, or audio/video synchronization. It proves the first required throughput gate: full-frame memory copy into the existing KMS dumb-buffer display path is viable on-device.

## Safety

- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
- No media assets, generated frames, PCM payloads, raw logs, boot images, or binaries are committed.
- Device returned to the `v2321` rollback checkpoint with `selftest fail=0`.
