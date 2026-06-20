# Native Init V2963 Bad Apple HUD Incremental Panel Source Build

## Summary

- Cycle: `V2963`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Decision: `v2963-badapple-hud-incremental-panel-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2963_badapple_hud_incremental_panel.img`
- Boot SHA256: `ea35fd8ffdcedee49ba79b2d4a7cf8800655706878d8200a868213b826910dd6`
- Init: `A90 Linux init 0.10.57 (v2963-badapple-hud-incremental-panel)`

## Why This Unit Exists

- V2955 confirmed the V2954 volume-only image still presented the full Bad Apple stream with `dropped_frames=0`, but the operator observed visible frame stutter.
- V2955/V2957/V2959 confirmed the pageflip path can present every frame, but it still reports alternating 16 ms / 50 ms flip-event cadence (`flip_delta_min_us≈166xx`, `flip_delta_max_us≈498xx`).
- V2962 proved the setcrtc full-song path presents all 6962 frames with no drops, but takes 275 s for a 232 s audio track (`fps_milli=25308`), so the next bottleneck is Player HUD per-frame render cost.
- V2963 keeps the setcrtc menu default and reduces Player HUD framebuffer writes by repainting the full static panel periodically while updating only dynamic text/bar regions each frame.

## Included Delta

- Adds `video.status.player_hud_incremental_panel=1` and keeps `video.status.version=7` for the optimized Player HUD renderer.
- Repaints the full static HUD panel every 60 frames or at session start, while clearing/redrawing only dynamic rows, progress, lamp, and beat-flash text on intervening frames.
- Keeps the APPS/DEMO Bad Apple launcher default at `--present setcrtc`; direct pageflip remains available for manual comparison.
- Keeps the V2952 Player HUD render fastpath, the V2960 setcrtc default, the full-song SD-cache asset, audio sync, beat flash, and the reduced Bad Apple menu PCM gain of `780`.
- Does not add Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths.

## Marker Check

- `A90 Linux init 0.10.57 (v2963-badapple-hud-incremental-panel)`
- `video.status.version=7`
- `video.status.player_hud_incremental_panel=1`
- `video.status.display_owner=1`
- `video.status.player_hud_fastpath=1`
- `menu.demo.badapple.action=play-av-fullsong`
- `menu.demo.badapple.frames=6962`
- `menu.demo.badapple.audio_pcm_gain_milli=780`
- `menu.demo.badapple.video_present=setcrtc`
- `menu.demo.badapple.audio_sync_start_offset_ms=450`
- `badapple-480x360-full-v2903`
- `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`
- `video.stream.flip_delta_min_us=%llu`
- `video.stream.flip_delta_max_us=%llu`
- `video.stream.flip_delta_avg_us=%llu`
- `video.stream.flip_delta_target_us=%llu`
- `video.stream.beat_flash.active_frames=%u`
- `audio.play.worker.pcm_gain_milli=%d`
- `audio.play.cap.duration_policy=%s`
- `badapple-fullsong-pcm`
- `kms-dumb-buffer`
- `player-hud`
- `mono1`

## Static Validation

- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V2963 identity, incremental HUD marker, setcrtc menu marker, trimmed gain marker, full-song asset hashes, and cadence counters.
- Device validation is deferred to V2964: flash this exact image and rerun the full-song Bad Apple Player HUD A/V path with setcrtc to compare elapsed time/fps against V2962.

## Bundled Runtime Metadata

- Bundled audio artifact count: `15`
- Replay entry count: `11`
- Native manifest SHA256: `b29d72ad5b844a2749279d78259e79c731db4d5f12cd546bfd3c3bd122ed6864`

## Safety

- No device action was performed by this builder.
- Generated frames, raw streams, boot images, and private caches remain private/untracked.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `badapple-hud-incremental-panel-candidate`.
