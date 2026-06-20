# Native Init V2985 DOOM Keyboard Caps Source Build

## Summary

- Cycle: `V2985`
- Track: active Video playback / DOOM input prerequisite.
- Decision: `v2985-doom-keyboard-caps-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2985_doom_keyboard_caps.img`
- Boot SHA256: `4ffdb9b6078e99b3c5f40db42c0c9ef9d01f7936006be33943a65d9965343e54`
- Init: `A90 Linux init 0.10.63 (v2985-doom-keyboard-caps)`
- Parent candidate: `v2983-inputcaps-touch-diag`.

## Branch Evidence

- V2984 live diagnostics proved `event6` and `event8` expose touch/MT capability bits and report `power.runtime_status=unsupported`, not `suspended`.
- Repeated V2982 live runs against `event6` reached the native `readinput` timeout with `0` captured events and clean rollback.
- Therefore the touch branch is not explained by missing capability or sysfs runtime-PM suspended state; the next recoverable path is the USB-keyboard fallback surface for DOOM input.

## Included Delta

- Extends `inputcaps <eventX>` decode output with DOOM-relevant keyboard capability bits: WASD, arrow keys, Enter, Space, Esc, Ctrl, and Shift.
- Keeps `inputscan` keyboard candidate classification and bounded `readinput` sampling unchanged.
- Adds no event injection, keymap changes, evdev grabs, touch configuration, or sysfs writes.
- Live validation is deferred: attach a USB keyboard/OTG path, flash this exact image, run `inputscan` and `inputcaps <keyboard-event>`, then bounded `readinput <keyboard-event> ...`.

## Marker Check

- `A90 Linux init 0.10.63 (v2985-doom-keyboard-caps)`
- `inputscan [eventX]`
- `inputcaps <eventX>`
- `readinput <eventX> [count] [timeout_ms]`
- `inputcaps.decode key_w=`
- `key_a=`
- `key_s=`
- `key_d=`
- `key_up=`
- `key_down=`
- `key_left=`
- `key_right=`
- `key_enter=`
- `key_space=`
- `key_esc=`
- `key_leftctrl=`
- `key_rightctrl=`
- `key_leftshift=`
- `key_rightshift=`
- `inputcaps.decode abs_x=`
- `power.runtime_status`

## Static Validation

- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains the V2985 identity plus expanded keyboard capability strings.

## Safety

- Host-side source build only; no device action in V2985.
- The changed command is read-only capability inventory from `/sys/class/input/<event>/device/capabilities/*`.
- No PMIC/backlight/GPIO/regulator/GDSC, Wi-Fi, audio route, video playback, or forbidden partition path is touched.
- Rollback target remains `v2321-usb-clean-identity-rodata` for the later live unit.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `doom-keyboard-fallback-caps-candidate`.
