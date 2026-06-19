# Native Init V2887 A/V Sync Drop Source Build

## Summary

- Cycle: `V2887`
- Track: active Video playback pipeline on existing KMS display.
- Decision: `v2887-av-sync-drop-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2887_av_sync_drop.img`
- Boot SHA256: `c9daccf175fdf794c6ef4d6c1cb02180380f041094de32a8afdcd161e11cb5aa`
- Init: `A90 Linux init 0.10.29 (v2887-av-sync-drop)`
- Parent validated state: V2886 proved audio-anchored video stream scheduling plus operator-visible page-flip checkerboard output.

## Included Delta

- Adds opt-in `video stream ... --sync-audio-status /cache/a90-audio-play/status.txt`.
- Waits for `audio.play.worker.listen_begin_ns` and sample/frame geometry before presenting frames.
- Anchors video frame deadlines to the audio PCM begin timestamp instead of video command start.
- Drops audio-sync page-flip frames that are already more than half a frame late instead of burst-presenting stale frames.
- Keeps the default non-sync `video stream` behavior unchanged.
- Restricts the sync status path to `/cache/a90-audio-play/status.txt` and bounds the wait with `--sync-wait-ms`.

## Validation

- `py_compile`: V2887 builder.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V2887 audio-sync drop markers plus retained audio timeline/page-flip markers.
- `video.stream.audio_sync.enabled=`
- `video.stream.audio_sync.ready=`
- `video.stream.audio_sync.listen_begin_ns=`
- `video.stream.audio_sync.anchor_age_ns=`
- `video.stream.requested_audio_sync=`
- `--sync-audio-status`
- `/cache/a90-audio-play/status.txt`
- `audio.play.worker.listen_begin_ns=`
- `audio.play.worker.listen_end_ns=`
- `kms-dumb-buffer-pageflip`
- `video.stream.audio_sync.drop_policy=`
- `video.stream.dropped_frames=`
- `video.stream.audio_sync.first_presented_frame=`
- `video.stream.audio_sync.initial_drop_late_ns=`
- Device validation is deferred to V2888: flash this exact image, run PCM audio + sync video stream with late-frame accounting, then rollback to `v2321`.

## Bundled Runtime Metadata

- Bundled audio artifact count: `15`
- Replay entry count: `11`
- Native manifest SHA256: `b29d72ad5b844a2749279d78259e79c731db4d5f12cd546bfd3c3bd122ed6864`

## Safety

- No device action was performed by this builder.
- This unit adds scheduling/observability only; it does not add Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.
- Audio amplitude and route behavior remain governed by existing bounded `audio play` caps.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `av-sync-drop-candidate`.
