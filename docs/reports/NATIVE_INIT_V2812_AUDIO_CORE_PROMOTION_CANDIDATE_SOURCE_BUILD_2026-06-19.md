# Native Init V2812 Audio Core 0.10.0 Promotion Candidate Source Build

## Summary

- Cycle: `V2812`
- Track: audio core promotion candidate.
- Decision: `v2812-audio-core-promotion-candidate-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2812_audio_core_promotion_candidate.img`
- Boot SHA256: `9cf680ae7dce1dac53b58a72e98668f5f6347bc14d6a64428f06ce2af830cdd0`
- Init: `A90 Linux init 0.10.0 (v2812-audio-core-promotion-candidate)`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v2334_audio_snd_nodes_preflight.img`

## Promotion Context

- V2811 proved the native `audio play --mode listen --execute` integrated path mechanically on device: worker start, ADSP/card/control, late manifest deploy, SET-cal, route, PCM write/drain, cleanup, and rollback all passed.
- GOAL.md and `docs/operations/VERSIONING_POLICY.md` require an epic-level MINOR roll when audio becomes the adopted promoted baseline, so this candidate resets the init version from `0.9.x` to `0.10.0`.
- This unit only builds the candidate. Adoption still requires a follow-up live validation of this exact boot image and an explicit docs/status promotion update.

## Included Audio Core

- Keeps the V2807 late-manifest wait source: `audio play` can start before private SET-cal artifacts are staged, then waits up to 90 s for the default runtime manifest.
- Keeps the V2804 no-wait foreground ADSP kick, native-width `/dev/msm_audio_cal` ioctl constants, `/dev/ion` and `/dev/msm_audio_cal` materialization, dmabuf `msync(EINVAL)` nonfatal handling, observed App-Type Config, corrected SET-cal order, route apply/reset, and bounded PCM playback.
- Safety profile remains `internal-speaker-safe`, listen amplitude 0.15, hard cap 0.2, no WSA smart-amp gain/boost writes.

## Scope Boundary

- No device action was performed by this builder.
- No audio ioctl, mixer write, route apply, PCM open, or playback occurs during build.
- Rollback target remains `v2321-usb-clean-identity-rodata` until this candidate is live-validated and explicitly adopted.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0`
- Candidate type: `promotion-candidate`, not yet the rollback baseline.
