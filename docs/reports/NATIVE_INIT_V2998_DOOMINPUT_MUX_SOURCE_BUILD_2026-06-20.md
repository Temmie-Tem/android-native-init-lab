# Native Init V2998 DOOM Input Mux Source Build

## Summary

- Cycle: `V2998`
- Track: active Video playback / DOOM input prerequisite.
- Decision: `v2998-doominput-mux-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2998_doominput_mux.img`
- Boot SHA256: `4828fdfba65c80a5d0a2883c2a8964a82074a6863e03e95f0f8f9aa1e9e138d6`
- Init: `A90 Linux init 0.10.67 (v2998-doominput-mux)`
- Parent candidate: `v2996-doominput-button-proxy`.

## Branch Evidence

- V2996 maps known A90 physical buttons into diagnostic DOOM state bits.
- V2997 stages sequential event3/event0 live sampling, but physical-button fallback spans more than one evdev node.
- A real DOOM input path needs a single state machine that can merge multiple read-only input sources.

## Included Delta

- Adds `doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]`.
- Opens up to four event nodes `O_RDONLY|O_NONBLOCK`, polls them together, and applies events to one `doominput_state`.
- Emits source-labelled `doominputmux.event` and `doominputmux.state` lines so event3 volume keys and event0 power can be validated in one bounded window.
- Keeps V2996 diagnostic button mappings: `KEY_VOLUMEUP` -> forward, `KEY_VOLUMEDOWN` -> back, `KEY_POWER` -> fire.
- Adds no input injection, evdev grabs, keymap changes, touch configuration, or sysfs writes.
- No PMIC/backlight/GPIO/regulator/GDSC writes, audio playback, video playback, or forbidden partition path is touched.

## Marker Check

- `A90 Linux init 0.10.67 (v2998-doominput-mux)`
- `doominputmux <eventX,eventY[,eventZ]> [count] [timeout_ms]`
- `doominputmux: waiting on %s (%d events across %d fds), q/Ctrl-C cancels`
- `doominputmux.event %d: source=%s type=%s code=%s role=%s value=%d`
- `doominputmux.state %d: source=%s forward=%d back=%d left=%d right=%d fire=%d`
- `doom_button_forward`
- `doom_button_back`
- `doom_button_fire`

## Static Validation

- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains the V2998 identity, `doominputmux` command surface, source-labelled state markers, and physical-button proxy role strings.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2998_doominput_mux.py tests/test_native_doominput_mux_source_v2998.py`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doominput_mux_source_v2998`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2998_doominput_mux.py`: PASS (source build and marker check)
- `file workspace/private/builds/native-init/v2998-doominput-mux/init_v2998_doominput_mux workspace/private/builds/native-init/v2998-doominput-mux/a90_android_execns_probe_v505_doominput_mux`: PASS (both AArch64 static ELF)
- `sha256sum workspace/private/inputs/boot_images/boot_linux_v2998_doominput_mux.img`: PASS (`4828fdfba65c80a5d0a2883c2a8964a82074a6863e03e95f0f8f9aa1e9e138d6`)
- `git diff --check`: PASS

## Safety

- Host-side source build only; no device action in V2998.
- Runtime behavior remains read-only: `doominputmux` opens `/dev/input/event*` `O_RDONLY|O_NONBLOCK`, polls, reads, and prints state.
- Rollback target remains `v2321-usb-clean-identity-rodata` for any later live unit.

## Next

- A later live handoff can flash this candidate and sample `doominputmux event3,event0` while the operator presses VOLUMEUP/VOLUMEDOWN/POWER.
- That live step remains diagnostic input liveness proof, not a final DOOM control scheme.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `doominput-mux-candidate`.
