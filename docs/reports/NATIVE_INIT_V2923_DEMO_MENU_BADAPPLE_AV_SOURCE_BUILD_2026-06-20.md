# Native Init V2923 DEMO Bad Apple A/V Menu Source Build

## Summary

- Cycle: `V2923`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Decision: `v2923-demo-menu-badapple-av-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2923_demo_menu_badapple_av.img`
- Boot SHA256: `212846f44bb707f0acb95a4c552753389e7f7588c3157009eca1c2b3008e3fa3`
- Init: `A90 Linux init 0.10.40 (v2923-demo-menu-badapple-av)`
- Parent live unit: V2920 proved the Bad Apple Player HUD A/V path; V2923 upgrades the bounded `DEMO > Bad Apple` menu launcher to start native PCM-file audio and video sync over the existing SD SHA-addressed cache.

## Included Delta

- Packages the `DEMO > Bad Apple` bounded A/V Player HUD menu launcher into a flashable test image.
- Keeps the full Bad Apple stream and PCM outside the boot image; boot carries only player/HUD code.
- Adds the `DEMO > Bad Apple` menu entry as a bounded 120-frame A/V Player HUD preview that starts a 4 s native PCM-file audio worker, syncs video to `/cache/a90-audio-play/status.txt`, and restores the menu after completion.
- Keeps `badapple-scale` as the prior full-frame synthetic/cache preset for regression comparison.
- Does not add Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths.

## Marker Check

- `A90 Linux init 0.10.40 (v2923-demo-menu-badapple-av)`
- `video.status.next_cache=video cache [status|verify|play] SHA256 [--trust-cache] [--present pageflip] [--layout full|player-hud] | video cache preset [badapple|badapple-scale] play [--trust-cache]`
- `video.status.next_demo=video demo [badapple|badapple-scale] [status|verify|play] [--trust-cache]`
- `DEMO >`
- `BAD APPLE HUD`
- `4S A/V PLAYER HUD`
- `menu.demo.badapple.frames=120`
- `menu.demo.badapple.restore=menu`
- `menu.demo.badapple.action=play-av-preview`
- `menu.demo.badapple.audio_duration_ms=4000`
- `menu.demo.badapple.audio_amplitude_milli=150`
- `menu.demo.badapple.audio_pcm=/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le`
- `menu.demo.badapple.audio_sync_status=/cache/a90-audio-play/status.txt`
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
- `BEAT FLASH: audio-clock border pulse (host onset table pending)`
- `READONLY TELEMETRY /proc+/sys`
- `/mnt/sdext/a90/runtime/video/cache`
- `video.cache.version=1`
- `video.cache.play.trust_cache=1`
- `video.cache.verify.actual_sha256=trust-cache-not-checked`
- `kms-dumb-buffer-pageflip`
- `mono1`

## Validation

- `py_compile`: V2923 builder.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V2923 identity, real Bad Apple preset SHA, player-hud layout strings, read-only telemetry HUD strings, and retained pageflip/mono1 markers.
- Device validation is deferred to V2924: flash this exact image, run `version`/`status`/`selftest`, inspect `video status`, then exercise the bounded menu preview if cache is present.

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
- Candidate type: `demo-menu-badapple-av-candidate`.
