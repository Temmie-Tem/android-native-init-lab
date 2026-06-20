# Native Init V2983 Inputcaps Touch Diagnostics Source Build

## Summary

- Cycle: `V2983`
- Track: active Video playback / DOOM input prerequisite.
- Decision: `v2983-inputcaps-touch-diag-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2983_inputcaps_touch_diag.img`
- Boot SHA256: `3edb059b7887cd0577a98bc28b41f1ce8c643b4234b7d3100896bb27aa86d226`
- Init: `A90 Linux init 0.10.62 (v2983-inputcaps-touch-diag)`

## Included Delta

- Expands `inputcaps <eventX>` from key-only output to read-only touch diagnostics for EV/KEY/ABS/PROP/SW capability bitmaps and runtime-PM state.
- Keeps V2981 bounded `readinput <eventX> [count] [timeout_ms]` support for later event sampling.
- Decodes the key touch bits needed for multitouch protocol B: `ABS_MT_SLOT`, `ABS_MT_TRACKING_ID`, `ABS_MT_POSITION_X`, `ABS_MT_POSITION_Y`, pressure/major, and `BTN_TOUCH`.
- Prints read-only `/sys/class/input/<event>/device/power/*` runtime PM attributes to distinguish capability presence from a suspended/non-emitting device.
- Does not open the event stream, inject input, alter keymaps, or write touch/sysfs state in this build unit.


## Marker Check

- `A90 Linux init 0.10.62 (v2983-inputcaps-touch-diag)`
- `inputscan [eventX]`
- `inputcaps <eventX>`
- `readinput <eventX> [count] [timeout_ms]`
- `inputcaps.event=`
- `inputcaps.cap.%s=%s`
- `inputcaps.cap.%s=<missing errno=%d>`
- `inputcaps.decode ev_syn=`
- `inputcaps.decode abs_x=`
- `mt_slot=`
- `mt_x=`
- `mt_y=`
- `mt_tracking_id=`
- `power.runtime_status`
- `power/runtime_status`

## Static Validation

- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains the V2983 identity plus expanded `inputcaps` capability/runtime-PM diagnostics strings.
- Live validation is deferred to V2984: flash this exact image and run `inputcaps event6` / `inputcaps event8` plus full `inputscan`, then rollback to V2321.

## Safety

- Host-side source build only; no device action in V2983.
- The command is read-only sysfs/capability inventory. The only runtime node action is the existing `/dev/input/event*` char-node materialization from `/sys/class/input/*/dev`.
- No PMIC/backlight/GPIO/regulator/GDSC, Wi-Fi, audio route, or forbidden partition path is touched.
- Rollback target remains `v2321-usb-clean-identity-rodata` for the later live unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `inputcaps-touch-diagnostics-candidate`.
