# Native Init V2948 Bad Apple PCM Gain Source Build

## Summary

- Cycle: `V2948`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Decision: `v2948-badapple-pcm-gain-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2948_badapple_pcm_gain.img`
- Boot SHA256: `29b05291ef638f51a5c1b4abd93e15650180f474890df82b1dd424699c315b5d`
- Init: `A90 Linux init 0.10.50 (v2948-badapple-pcm-gain)`
- Parent live unit: V2947 proved full-length Bad Apple Player HUD A/V playback with audio heard, 6962/6962 frames presented, zero dropped frames, and full PCM worker completion; V2948 keeps that path and adds attenuation-only PCM gain for slightly lower volume.

## Included Delta

- Adds attenuation-only `--pcm-gain-milli` support for PCM-file playback, preserving the path-scoped `badapple-fullsong-pcm` duration policy and 64-bit long PCM frame geometry.
- Keeps the full Bad Apple stream and PCM outside the boot image; boot carries only player/HUD/audio policy code.
- Keeps `--sync-start-offset-ms` and changes the sync drop policy to drop only when the frame is more than one frame interval late, instead of more than a half-frame late.
- Keeps `badapple-scale` as the prior full-frame synthetic/cache preset for regression comparison.
- Does not add Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths.

## Marker Check

- `A90 Linux init 0.10.50 (v2948-badapple-pcm-gain)`
- `video.status.next_cache=video cache [status|verify|play] SHA256 [--trust-cache] [--present pageflip] [--layout full|player-hud] | video cache preset [badapple|badapple-scale] play [--trust-cache]`
- `video.status.next_demo=video demo [badapple|badapple-scale] [status|verify|play] [--trust-cache]`
- `DEMO >`
- `BAD APPLE HUD`
- `menu.demo.badapple.frames=300`
- `menu.demo.badapple.restore=menu`
- `menu.demo.badapple.action=play-av-preview`
- `menu.demo.badapple.audio_duration_ms=10000`
- `menu.demo.badapple.audio_amplitude_milli=200`
- `menu.demo.badapple.audio_pcm=/cache/a90-runtime/pkg/av/v2933/audio/badapple_preview200_limited.s16le`
- `menu.demo.badapple.audio_sync_status=/cache/a90-audio-play/status.txt`
- `menu.demo.badapple.audio_sync_start_offset_ms=450`
- `--sync-start-offset-ms`
- `video.stream.audio_sync.start_offset_ms=%u`
- `video.stream.audio_sync.corrected_anchor_ns=%llu`
- `video.stream.audio_sync.drop_threshold_ns=%llu`
- `video.stream.requested_audio_sync_start_offset_ms=%u`
- `video.cache.play.requested_audio_sync_start_offset_ms=%u`
- `menu.demo.badapple.audio_rc=%d`
- `badapple-480x360-full-v2903`
- `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- `badapple-scale`
- `878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890`
- `video.cache.preset=%s`
- `video.cache.preset.asset_id=%s`
- `video.cache.preset.sha256=%s`
- `video.cache.play.requested_layout=%s`
- `video.stream.requested_layout=%s`
- `video.stream.layout=%s`
- `player-hud`
- `DEMO / BAD APPLE`
- `A90 PLAYER HUD`
- `BEAT FLASH %s  audio-clock onsets=%u nearest=%ums`
- `video.stream.beat_flash.enabled=1`
- `video.stream.beat_flash.source=%s`
- `badapple-v2903-energy-onsets-v2941`
- `video.stream.beat_flash.active_frames=%u`
- `audio.play.cap.effective_duration_ms=%d`
- `audio.play.cap.duration_policy=%s`
- `audio.play.cap.badapple_fullsong_ms=%d`
- `audio.play.cap.badapple_fullsong_sha256=%s`
- `audio.play.execute.total_frames=%lld`
- `audio.play.worker.total_frames=%lld`
- `--pcm-gain-milli`
- `audio.play.pcm_gain_milli=%d`
- `audio.play.pcm_gain.attenuation_only=1`
- `audio.play.execute.plan.pcm_gain_milli=%d`
- `audio.play.pcm_file.scaled_peak_abs=%d`
- `audio.play.execute.pcm_gain_milli=%d`
- `audio.play.worker.pcm_gain_milli=%d`
- `badapple-fullsong-pcm`
- `/cache/a90-runtime/pkg/av/v2903/audio/audio.s16le`
- `/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le`
- `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`
- `READONLY TELEMETRY /proc+/sys`
- `/mnt/sdext/a90/runtime/video/cache`
- `video.cache.version=1`
- `video.cache.play.trust_cache=1`
- `video.cache.verify.actual_sha256=trust-cache-not-checked`
- `kms-dumb-buffer-pageflip`
- `mono1`
- `audio.play.execute.sequence=adsp,snd,app_type,setcal_hold,route_playback,pcm,route_playback_reset,setcal_deallocate`
- `audio.play.integrated.sequence=adsp,snd,app_type,manifest_wait,setcal_hold,route_playback,pcm,route_playback_reset,setcal_deallocate`
- `audio.stop.requires.route_reset_playback=1`
- `audio route %s --reset --layer playback`
- `audio route %s --apply --layer playback`
- `route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|playback|blocked]`

## Validation

- `py_compile`: V2948 builder.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V2948 identity, real Bad Apple preset SHA, Player HUD sync-offset/drop-threshold strings, BEAT FLASH table/source markers, full-song audio cap, PCM64 geometry, and attenuation-only PCM gain markers, read-only telemetry HUD strings, and retained pageflip/mono1 markers.
- Device validation is deferred to V2949: flash this exact image, run a full-length Bad Apple Player HUD A/V pass, and confirm presented/total, audio completion, beat-flash activity, and `selftest fail=0`.

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
- Candidate type: `badapple-pcm-gain-candidate`.
