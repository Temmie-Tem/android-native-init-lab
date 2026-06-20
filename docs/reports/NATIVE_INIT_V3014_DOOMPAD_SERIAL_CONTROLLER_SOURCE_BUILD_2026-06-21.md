# Native Init V3014 DOOMPAD Serial Controller Source Build

## Summary

- Cycle: `V3014`
- Track: active Video playback / DOOM input handoff.
- Decision: `v3014-doompad-serial-controller-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3014_doompad_serial_controller.img`
- Boot SHA256: `5bdcab90807fe03f1f97717e4b371bce6c3567ad1f7635b51babb77b83b61455`
- Init: `A90 Linux init 0.10.70 (v3014-doompad-serial-controller)`
- Parent gate: `v3013-doom-precondition-stop`.

## Branch Evidence

- Touch-class input and physical-button mux samples previously produced zero DOOM state events.
- The USB keyboard/OTG fallback was operationally awkward because it requires host/device role changes and manual keyboard re-plugging.
- V3014 stages a host-serial virtual controller surface so validation can drive DOOM intent through the existing command channel without OTG hardware.

## Included Delta

- Adds `doompad [status|reset|key <role> <0|1>|tap <role>]` as a native-init command.
- Keeps a persistent native-init-memory-only DOOM button state for `forward`, `back`, `left`, `right`, `fire`, `use`, `menu`, and `run`.
- Emits stable `doompad.version`, `doompad.source`, `doompad.event`, and `doompad.state` lines for scripted validation.
- Updates `video status`, `video demo doom status`, and the DOOM menu entry to point at the serial `doompad` path.
- Leaves `doominput` and `doominputmux` intact as read-only evdev diagnostics and keeps USB keyboard/OTG only as a fallback note.
- Adds no DOOM WAD, gameplay loop, evdev injection, uinput, sysfs write, PMIC/backlight/GPIO/regulator/GDSC path, Wi-Fi action, or forbidden partition path.

## Marker Check

- `A90 Linux init 0.10.70 (v3014-doompad-serial-controller)`
- `video.status.doom_stub=1`
- `video.status.doom_input=serial-doompad-staged`
- `doompad [status|reset|key <role> <0|1>|tap <role>]`
- `doompad.version=1`
- `doompad.source=serial-control`
- `doompad.event seq=`
- `doompad.state seq=`
- `video.demo.status=blocked-gameplay-loop`
- `video.demo.input=serial-doompad-staged`
- `video.demo.input.virtual_controller=doompad-serial-v3014`
- `video.demo.input.hardware_gate=none-serial-control`
- `video.demo.input.command=doompad key <role> <0|1>`
- `menu.demo.doom.status=blocked-gameplay-loop`
- `menu.demo.doom.input.virtual_controller=doompad-serial-v3014`
- `menu.demo.doom.input.command=doompad key <role> <0|1>`
- `SERIAL DOOMPAD STATUS`

## Static Validation

- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains the V3014 identity plus serial `doompad` command/status strings.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v3014_doompad_serial_controller.py tests/test_native_doompad_serial_controller_source_v3014.py tests/test_native_doom_status_stub_source_v3000.py tests/test_native_doom_keyboard_gate_status_source_v3005.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doompad_serial_controller_source_v3014 tests.test_native_doom_status_stub_source_v3000 tests.test_native_doom_keyboard_gate_status_source_v3005`: PASS (`16` tests)
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3014_doompad_serial_controller.py`: PASS (source build and marker check)
- `file workspace/private/builds/native-init/v3014-doompad-serial-controller/init_v3014_doompad_serial_controller workspace/private/builds/native-init/v3014-doompad-serial-controller/a90_android_execns_probe_v508_doompad_serial_controller`: PASS (both AArch64 static ELF)
- `sha256sum workspace/private/inputs/boot_images/boot_linux_v3014_doompad_serial_controller.img`: PASS (`5bdcab90807fe03f1f97717e4b371bce6c3567ad1f7635b51babb77b83b61455`)
- `git diff --check`: PASS

## Safety

- Host-side source build only; no device action in V3014.
- `doompad` mutates only native-init memory reachable through the serial shell; it does not open `/dev/input`, write sysfs, inject events, or touch storage/partition state.
- Rollback target remains `v2321-usb-clean-identity-rodata` for any later live unit.

## Next

- Flash this exact candidate only after rollback image and recovery gates are re-confirmed.
- Live validation should run `doompad status`, a bounded key down/up sequence, `doompad reset`, `version`, `status`, and `selftest`, then rollback to V2321.
- A later unit can wire the actual DOOM gameplay loop to consume this state surface.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `doompad-serial-controller-candidate`.
