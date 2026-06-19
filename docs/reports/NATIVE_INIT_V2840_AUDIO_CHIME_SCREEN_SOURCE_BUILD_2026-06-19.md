# Native Init V2840 Audio Chime Screen Source Build

## Summary

- Cycle: `V2840`
- Track: post-promotion audio productization.
- Decision: `v2840-audio-chime-screen-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2840_audio_chime_screen.img`
- Boot SHA256: `57a61bf47f5da326d7faf6a9fcf1284accf6f9628b4a8bb25679a670c31dbb58`
- Init: `A90 Linux init 0.10.11 (v2840-audio-chime-screen)`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v2334_audio_snd_nodes_preflight.img`

## Included Delta

- Keeps the promoted audio core and rolls PATCH to `0.10.11` for a manual `audio chime` screen/menu surface.
- Adds display-only `screenapp audio-chime` and APPS/AUDIO `CHIME` entry for the V2838/V2839 manual chime preset.
- The screen shows the manual command, default amplitude `80` milli, default duration `1200` ms, V2839 validation, and rollback status.
- Boot autoplay remains disabled: the screen reports `BOOT AUTOPLAY DISABLED BLOCKS_BOOT=0` and does not run playback.

## Scope Boundary

- No device action was performed by this builder.
- No audio ioctl, mixer write, route apply, PCM open, or playback occurs during build.
- Rollback target remains `v2321-usb-clean-identity-rodata`; this artifact needs follow-up live validation before any adoption decision.

## Validation

- `py_compile`: builder and focused tests.
- `unittest`: V2840 chime screen, V2840 builder, and adjacent audio menu/screenapp/play-plan regression tests.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0`
- Candidate type: `audio-productization-candidate`.
