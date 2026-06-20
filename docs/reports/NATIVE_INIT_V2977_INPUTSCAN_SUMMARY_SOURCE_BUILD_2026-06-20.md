# Native Init V2977 Inputscan Summary Source Build

## Summary

- Cycle: `V2977`
- Track: active Video playback / DOOM input prerequisite.
- Decision: `v2977-inputscan-summary-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2977_inputscan_summary.img`
- Boot SHA256: `52a5d0329f8c42f360772e4541f77d31d4f3569e7e01aa086d17ed655a4349aa`
- Init: `A90 Linux init 0.10.60 (v2977-inputscan-summary)`

## Included Delta

- Adds `inputscan [eventX]`, a read-only evdev inventory command for the DOOM input prerequisite.
- Enumerates `/sys/class/input/event*`, materializes existing `/dev/input/event*` char nodes through the existing helper path, and prints each event name/dev/node.
- Classifies touch candidates from `EV_ABS` plus `BTN_TOUCH`, `ABS_X/Y`, or `ABS_MT_POSITION_X/Y`.
- Classifies keyboard fallback candidates from `EV_KEY` plus WASD/Enter/Space/Esc capability bits.
- Classifies physical-button candidates from power/volume key capability bits.
- Does not read event streams, block for input, inject input, alter keymaps, or touch display/audio/network state.

## Marker Check

- `A90 Linux init 0.10.60 (v2977-inputscan-summary)`
- `inputscan [eventX]`
- `inputscan.summary events=`
- `touch_candidates=`
- `keyboard_candidates=`
- `button_candidates=`
- `btn_touch=`
- `mt_xy=`
- `key_wasd=`
- `key_enter_space_esc=`

## Static Validation

- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains the V2977 identity and `inputscan` summary/classification strings.
- Live validation is deferred to V2978: flash this exact image, run `inputscan`, and if a touch candidate appears run a bounded `readinput <event> 1` human-touch sample.

## Safety

- Host-side source build only; no device action in V2977.
- The command is read-only sysfs/capability inventory. The only runtime node action is the existing `/dev/input/event*` char-node materialization from `/sys/class/input/*/dev`.
- No PMIC/backlight/GPIO/regulator/GDSC, Wi-Fi, audio route, or forbidden partition path is touched.
- Rollback target remains `v2321-usb-clean-identity-rodata` for the later live unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `inputscan-summary-candidate`.
