# Native Init V3025 DOOMGENERIC Command Bridge Source Build

## Summary

- Cycle: `V3025`
- Track: active Video playback / DOOM capstone.
- Decision: `v3025-doomgeneric-command-bridge-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3025_doomgeneric_command_bridge.img`
- Boot SHA256: `d028ece642793a7a6242295c86cd6caedbd533f733282120c0575116f012e95f`
- Init: `A90 Linux init 0.10.73 (v3025-doomgeneric-command-bridge)`

## Included Delta

- Adds the `a90_doomgeneric_bridge` native-init module and `video demo doom engine-probe` command surface.
- Bundles the V3024 private doomgeneric engine probe helper into the private ramdisk as a boot candidate helper.
- Keeps serial control as the primary input path: `serial-doompad-to-DG_GetKey`.
- Keeps sound disabled for the first bridge candidate: `-nosound -nomusic`.
- Keeps WAD/IWAD bytes out of public, ramdisk, and boot image; the command surface records only the runtime-private WAD root.

## Private Engine Helper

- Bundled helper path: `/bin/a90_doomgeneric_private_engine_v3024`
- V3024 engine binary: `workspace/private/builds/native-init/v3024-doomgeneric-private-integration/a90_doomgeneric_private_engine_v3024`
- V3024 engine SHA256: `8b6630498b7ff217e6ad9b27593f89644ba73eb7cbbf11361838972f15581735`
- V3024 engine bytes: `597960`
- Helper bundled in ramdisk: `1`
- WAD files in ramdisk: `0`
- Runtime WAD root: `/cache/a90-runtime/pkg/doom/v3024/`

## Command Surface

- `video status`: reports `video.status.doomgeneric.*` helper, input, and WAD embedding markers.
- `video demo doom status`: retains legacy doompad-loop markers and adds `video.demo.engine.active` / helper state.
- `video demo doom engine-probe`: runs the V3024 helper with a bounded 3000 ms timeout and reports `video.demo.doom.engine_probe.rc`.
- Menu status remains status-only; it does not launch WAD-backed gameplay.

## Marker Check

- `A90 Linux init 0.10.73 (v3025-doomgeneric-command-bridge)`
- `v3025-doomgeneric-command-bridge`
- `doomgeneric-private-link-v3025`
- `/bin/a90_doomgeneric_private_engine_v3024`
- `/cache/a90-runtime/pkg/doom/v3024/`
- `serial-doompad-to-DG_GetKey`
- `disabled-nosound-nomusic`
- `video demo doom engine-probe`
- `video.demo.engine.helper.present=%d`
- `video.demo.asset.wad.embedded_in_boot=%d`
- `video.demo.input.otg_required=0`
- `a90.doomgeneric.v3024.private_source_integration=1`
- `a90.doomgeneric.v3024.wad_policy=runtime-private-not-boot`
- `a90.doomgeneric.v3024.input=serial-doompad-to-DG_GetKey`

## Safety

- No device action was performed by this builder.
- No flash, serial command, Wi-Fi action, sysfs write, evdev injection, uinput, PMIC, regulator, backlight, GPIO, GDSC, or forbidden partition path is touched.
- The generated boot image is private/untracked. Public output is limited to source, tests, and this metadata-only report.
- WAD/IWAD bytes are not copied; full gameplay remains blocked on a later runtime-private WAD staging/live-validation unit.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Host Validation

- `py_compile`: builder, selector, and focused tests.
- `unittest`: V3025 command bridge tests and selector tests.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack with V3024 private engine helper, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3025 command bridge markers plus V3024 private engine bridge markers.
- Ramdisk inventory: helper path present and WAD file count is zero.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3026`
- Type: rollback-gated live validation of V3025 command bridge.
- Scope: flash only the exact V3025 boot image through `native_init_flash.py`, health-check, run `video demo doom status` and `video demo doom engine-probe`, then rollback to V2321.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3024", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/cache/a90-runtime/pkg/doom/v3024/"`
- Candidate type: `doomgeneric-command-bridge-candidate`.
