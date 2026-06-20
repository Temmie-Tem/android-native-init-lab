# Native Init V3005 DOOM Keyboard Gate Status Source Build

## Summary

- Cycle: `V3005`
- Track: active Video playback / DOOM input prerequisite.
- Decision: `v3005-doom-keyboard-gate-status-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3005_doom_keyboard_gate_status.img`
- Boot SHA256: `51efe32f28cfbeae62c5b5d6ccc9b21e65718030ff4bbfe64228f9a155ece622`
- Init: `A90 Linux init 0.10.69 (v3005-doom-keyboard-gate-status)`
- Parent gate: `v3004-doominput-keyboard-live-gate`.

## Branch Evidence

- V3002 proved `event3,event0` are button-capable but captured zero mux events/states during the bounded live window.
- V3003 recorded the DOOM input frontier as hardware-stimulus-gated and warned against repeating the same physical-button mux run without confirmed button input.
- V3004 staged the higher-information USB keyboard/OTG live gate on the V2989 `doominput.state` candidate.
- This source build updates the on-device DOOM status/menu text so it no longer points operators back at the stale physical-button mux command.

## Included Delta

- Keeps the `DOOM` DEMO entry status-only with `verify` and `play` still blocked by `-EAGAIN`.
- Reports built-in touch as zero-event and physical-button mux as `v3002-zero-event-do-not-repeat`.
- Reports the current next gate as `v3004-doominput-keyboard-live-gate` with `usb-keyboard-otg` hardware required.
- Exposes the diagnostic command shape as `doominput <keyboard-event> 32 60000` instead of the stale `doominputmux event3,event0` sample.
- Adds no DOOM WAD, gameplay loop, input sampling, input injection, video/audio playback, sysfs write, PMIC/backlight/GPIO/regulator/GDSC path, Wi-Fi action, or forbidden partition path.

## Marker Check

- `A90 Linux init 0.10.69 (v3005-doom-keyboard-gate-status)`
- `video.status.doom_stub=1`
- `video.status.doom_input=not-proven`
- `video.demo.status=blocked-input-prerequisite`
- `video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat`
- `video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate`
- `video.demo.input.hardware_gate=usb-keyboard-otg`
- `video.demo.input.command=doominput <keyboard-event> 32 60000`
- `menu.demo.doom.action=status-only`
- `menu.demo.doom.input.live_handoff=v3004-doominput-keyboard-live-gate`
- `menu.demo.doom.input.command=doominput <keyboard-event> 32 60000`

## Static Validation

- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains the V3005 identity and current keyboard-gate DOOM status strings.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v3005_doom_keyboard_gate_status.py tests/test_native_doom_keyboard_gate_status_source_v3005.py tests/test_native_doom_status_stub_source_v3000.py`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_keyboard_gate_status_source_v3005 tests.test_native_doom_status_stub_source_v3000`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3005_doom_keyboard_gate_status.py`: PASS (source build and marker check)
- `file workspace/private/builds/native-init/v3005-doom-keyboard-gate-status/init_v3005_doom_keyboard_gate_status workspace/private/builds/native-init/v3005-doom-keyboard-gate-status/a90_android_execns_probe_v507_doom_keyboard_gate_status`: PASS (both AArch64 static ELF)
- `sha256sum workspace/private/inputs/boot_images/boot_linux_v3005_doom_keyboard_gate_status.img`: PASS (`51efe32f28cfbeae62c5b5d6ccc9b21e65718030ff4bbfe64228f9a155ece622`)
- `git diff --check`: PASS

## Safety

- Host-side source build only; no device action in V3005.
- The new DOOM surface is status-only and does not start playback or sample input.
- Rollback target remains `v2321-usb-clean-identity-rodata` for any later live unit.

## Next

- Run the V3004 live gate only when USB keyboard/OTG is attached and an operator can press DOOM keys during the single bounded sample window.
- If keyboard state is proven, the next DOOM branch can wire a minimal game input path; if it times out, keep the blocker visible and avoid repeating no-stimulus samples.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `doom-keyboard-gate-status-candidate`.
