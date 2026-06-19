# Native Init V2883 A/V Sync Telemetry Source Build

## Summary

- Cycle: `V2883`
- Track: active Video playback pipeline; this unit adds the audio timeline anchor needed for exact A/V sync.
- Decision: `v2883-av-sync-telemetry-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2883_av_sync_telemetry.img`
- Boot SHA256: `8bd3931850850aaa871a5765a0c22aa851e8c2a2c4efd815dfb61c7b5ff64c53`
- Init: `A90 Linux init 0.10.27 (v2883-av-sync-telemetry)`
- Parent validated state: V2882 live-proved PCM-file audio and page-flip video can co-run in one boot.

## Included Delta

- Keeps the bounded `audio play --pcm-file` source and the KMS page-flip `video stream` path unchanged.
- Adds monotonic `listen_begin_ns` immediately before the first PCM write and `listen_end_ns` after drain/abort.
- Records sample rate, channels, bit width, frame bytes, total frames/bytes, expected duration, frames done, and bytes done.
- Emits the same timeline markers to the async worker status file so the video runner can read them while/after playback.
- Makes no mixer, route, SET-cal, audio amplitude, video KMS, or flash-policy change.

## Telemetry Contract

- Version: `1`
- Audio begin anchor: `audio.play.worker.listen_begin_ns`
- Audio end anchor: `audio.play.worker.listen_end_ns`
- Status mirror: `/cache/a90-audio-play/status.txt`
- Sync formula for the next unit: audio frame position = `(now_ns - listen_begin_ns) * sample_rate / 1e9`, bounded by `total_frames`.
- Video clock input: retained DRM page-flip `video.stream.last_timestamp_us` plus per-run elapsed/flip counters.

## Bundled Runtime Metadata

- Bundled audio artifact count: `15`
- Replay entry count: `11`
- Native manifest SHA256: `b29d72ad5b844a2749279d78259e79c731db4d5f12cd546bfd3c3bd122ed6864`
- Raw SET-cal bytes remain private; this report records only counts and hashes.

## Static Validation

- `py_compile`: V2883 builder.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V2883 timeline, retained PCM-file, and retained page-flip markers.
- `audio.play.execute.timeline.version=1`
- `audio.play.execute.listen_begin_ns=`
- `audio.play.execute.listen_end_ns=`
- `audio.play.execute.expected_duration_ns=`
- `audio.play.worker.timeline.version=1`
- `audio.play.worker.listen_begin_ns=`
- `audio.play.worker.listen_end_ns=`
- `audio.play.worker.frames_done=`
- `audio.play.worker.expected_duration_ns=`
- `audio.play.pcm_file_supported=1`
- `--pcm-file PATH`
- `kms-dumb-buffer-pageflip`
- `file`: native-init and helper are AArch64 statically linked executables.
- Device validation is deferred to V2884: flash this exact image, run the V2882-style A/V co-run, require timeline markers, then rollback to `v2321`.

## Safety

- No device action was performed by this builder.
- This unit adds observability only; it does not add new Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.
- PCM execution remains bounded by existing audio caps and pre-write amplitude scanning.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `av-sync-telemetry-candidate`.
