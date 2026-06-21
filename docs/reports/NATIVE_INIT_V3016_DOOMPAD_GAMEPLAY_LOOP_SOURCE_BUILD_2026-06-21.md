# Native Init V3016 DOOMPAD Gameplay Loop Source Build

## Summary

- Cycle: `V3016`
- Track: active Video playback / DOOM input handoff.
- Decision: `v3016-doompad-gameplay-loop-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3016_doompad_gameplay_loop.img`
- Boot SHA256: `e5303f7b79b8ebc100ffd5361c965753c6e325a94d3b6f3316d13ebcd22006e6`
- Init: `A90 Linux init 0.10.71 (v3016-doompad-gameplay-loop)`
- Parent gate: `v3015-doompad-serial-controller-serial-state-pass-before-rollback`.

## Branch Evidence

- V3015 proved the serial command bridge can mutate a native-init-memory-only DOOMPAD state and rollback cleanly to V2321.
- OTG keyboard use remains operationally awkward because host mode and keyboard re-plugging interrupt the normal command path.
- V3016 wires the already-proven `doompad` state into a bounded foreground KMS loop so the command channel can prove input consumption without `/dev/input` injection.

## Included Delta

- Adds `video demo doom verify` and `video demo doom play [frames]` as a bounded KMS frame loop that consumes the current `doompad` snapshot.
- Emits stable `doomplay.version`, `doomplay.source`, `doomplay.consumed_doompad_seq`, `doomplay.input.*`, `doomplay.player.*`, and `doomplay.frames_presented` lines.
- Keeps the loop foreground and bounded: default `90` frames, verify `1` frame, max `300` frames.
- Updates `video demo doom status` and the DOOM menu status to report `serial-doompad-consumed` rather than a blocked gameplay loop.
- Leaves `doompad` as native-init memory only; no evdev open, `uinput`, `EVIOCGRAB`, sysfs write, key injection, Wi-Fi action, or forbidden partition path is added.
- Does not bundle a WAD or claim `doomgeneric`; this is a DOOMPAD gameplay-loop proof surface.

## Marker Check

- `A90 Linux init 0.10.71 (v3016-doompad-gameplay-loop)`
- `video.status.doom_stub=1`
- `video.status.doom_input=serial-doompad-staged`
- `doompad [status|reset|key <role> <0|1>|tap <role>]`
- `doompad.version=1`
- `doompad.source=serial-control`
- `video.demo.asset_id=doompad-loop-v3016`
- `video.demo.status=doompad-frame-loop-ready`
- `video.demo.engine=doompad-loop-not-doomgeneric`
- `video.demo.asset.wad=not-bundled`
- `video.demo.gameplay_loop=doompad-kms-v3016`
- `video.demo.input=serial-doompad-consumed`
- `video.demo.input.virtual_controller=doompad-serial-v3014`
- `video.demo.input.consumed=doompad-serial-v3014`
- `video.demo.input.hardware_gate=none-serial-control`
- `video.demo.input.command=doompad key <role> <0|1>`
- `video.demo.play.command=video demo doom play [frames]`
- `doomplay.version=1`
- `doomplay.source=doompad-state`
- `doomplay.frames_presented=`
- `doomplay.consumed_doompad_seq=`
- `doomplay.player.x=`
- `video.demo.doom.play=doompad-frame-loop`
- `menu.demo.doom.status=doompad-frame-loop-ready`
- `menu.demo.doom.input.consumed=doompad-serial-v3014`
- `menu.demo.doom.play.command=video demo doom play [frames]`
- `SERIAL DOOMPAD STATUS`

## Static Validation

- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains the V3016 identity plus DOOMPAD state-consumer and gameplay-loop strings.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v3016_doompad_gameplay_loop.py tests/test_native_doompad_gameplay_loop_source_v3016.py tests/test_native_doompad_serial_controller_source_v3014.py tests/test_native_doom_status_stub_source_v3000.py tests/test_native_doom_keyboard_gate_status_source_v3005.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doompad_gameplay_loop_source_v3016 tests.test_native_doompad_serial_controller_source_v3014 tests.test_native_doom_status_stub_source_v3000 tests.test_native_doom_keyboard_gate_status_source_v3005`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3016_doompad_gameplay_loop.py`: PASS (source build and marker check)
- `file workspace/private/builds/native-init/v3016-doompad-gameplay-loop/init_v3016_doompad_gameplay_loop workspace/private/builds/native-init/v3016-doompad-gameplay-loop/a90_android_execns_probe_v509_doompad_gameplay_loop`: PASS (both AArch64 static ELF)
- `sha256sum workspace/private/inputs/boot_images/boot_linux_v3016_doompad_gameplay_loop.img`: PASS (`e5303f7b79b8ebc100ffd5361c965753c6e325a94d3b6f3316d13ebcd22006e6`)
- `git diff --check`: PASS

## Safety

- Host-side source build only; no device action in V3016.
- The gameplay loop reads only the in-memory `doompad` snapshot and writes only KMS frames plus serial status lines.
- Rollback target remains `v2321-usb-clean-identity-rodata` for any later live unit.

## Next

- Flash this exact candidate only after rollback image and recovery gates are re-confirmed.
- Live validation should set `doompad key forward 1` and `doompad key fire 1`, run `video demo doom play 8`, prove the frame loop consumed those bits, then reset and rollback to V2321.
- A later unit can replace this proof surface with a real WAD-backed engine if a boot-size and asset policy are chosen.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `doompad-gameplay-loop-candidate`.
