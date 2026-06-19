# Native Init V2849 Audio Status Productization Source Build

## Summary

- Cycle: `V2849`
- Track: post-promotion audio productization / readable operation.
- Decision: `v2849-audio-status-productization-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2849_audio_status_productization.img`
- Boot SHA256: `4f818d7d2f910225bb37ce502bdaf37853053b5889fb699cd8e5ca6e6690b5f6`
- Init: `A90 Linux init 0.10.15 (v2849-audio-status-productization)`
- Parent candidate: `v2847-audio-stop-execute`

## Included Delta

- Keeps the bundled SET-cal manifest/payload package, best-effort boot chime, and bounded `audio stop --execute` from V2847.
- Adds read-only `audio.status.productization.*` markers so host automation can identify the latest proven audio feature set without parsing long reports.
- Adds explicit `audio.status.feature.boot_chime.*` and `audio.status.feature.stop_execute.*` markers.
- Updates `screenapp audio-status` to show the latest productization run/version plus boot-chime and stop-execute state.

## Productization Markers

- Marker version: `1`
- Latest proven run: `V2848`
- Latest proven version: `0.10.14`
- Latest proven tag: `v2847-audio-stop-execute`
- Boot-chime validation: `V2846`
- Stop-execute validation: `V2848`
- Stop-execute scope: `core-route-reset`
- Live validation state: `pending`

## Bundled Runtime Metadata

- Bundled artifact count: `15`
- Replay entry count: `11`
- Native manifest SHA256: `b29d72ad5b844a2749279d78259e79c731db4d5f12cd546bfd3c3bd122ed6864`
- Boot chime enabled: `1`
- Stop execute supported: `1`
- Raw SET-cal bytes remain private; this report records only counts and hashes.

## Validation

- `py_compile`: builder and focused tests.
- `unittest`: source markers, screen status markers, and build wrapper contract tests.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.
- Next live unit should flash this exact image, read `audio status` / `screenapp audio-status`, verify the productization markers, and rollback to `v2321`.

## Safety

- No device action was performed by this builder.
- This unit adds read-only status and display labels only; it does not add new mixer, PCM, route, SET-cal, or smart-amp writes.
- Private raw payloads are not committed; they are only copied into the private generated boot image.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `audio-productization-status-candidate`.
