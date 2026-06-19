# Native Init V2905 Video SD Cache Command Source Build

## Summary

- Cycle: `V2905`
- Track: active Video playback pipeline on existing KMS display.
- Decision: `v2905-video-cache-command-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2905_video_cache_command.img`
- Boot SHA256: `e57b48bb4c6e5a7139c2630c9ed88a7a5d9c0461e6aebef8b9a056704347c62f`
- Init: `A90 Linux init 0.10.34 (v2905-video-cache-command)`
- Parent code unit: V2904 added `video cache status|verify|play SHA256` over the existing `A90VSTR1` stream player.

## Included Delta

- Builds the V2904 SD-cache command surface into a flashable test image.
- Keeps large video assets on the SD SHA-addressed cache; the boot image carries only player and verification code.
- `video cache status` reports manifest and stream-size state without hashing the multi-GB stream.
- `video cache verify` and `video cache play` require a full SHA-256 stream match before playback.
- Playback still reuses the existing KMS dumb-buffer stream path; no Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is added.

## Marker Check

- `A90 Linux init 0.10.34 (v2905-video-cache-command)`
- `video.status.next_cache=video cache [status|verify|play] SHA256 [--present pageflip]`
- `video.cache.version=1`
- `/mnt/sdext/a90/runtime/video/cache`
- `sha256-`
- `video.cache.stream_size_match=`
- `video.cache.verify.sha256_match=`
- `video.cache.play.requested_present=`
- `video cache [status|verify|play] SHA256`
- `kms-dumb-buffer-pageflip`
- `mono1`
- `video.stream.frames_total=`
- `video.stream.dropped_frames=`

## Validation

- `py_compile`: V2905 builder.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains the V2905 init identity, video cache command markers, SD cache path, and retained video stream/pageflip markers.
- Device validation is deferred to V2906: flash this exact image, run `video cache status|verify|play` against the V2900 SD cache SHA, then rollback to `v2321`.

## Bundled Runtime Metadata

- Bundled audio artifact count: `15`
- Replay entry count: `11`
- Native manifest SHA256: `b29d72ad5b844a2749279d78259e79c731db4d5f12cd546bfd3c3bd122ed6864`

## Safety

- No device action was performed by this builder.
- This unit changes the command surface only; generated frames, raw streams, and boot images remain private/untracked.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `video-cache-command-candidate`.
