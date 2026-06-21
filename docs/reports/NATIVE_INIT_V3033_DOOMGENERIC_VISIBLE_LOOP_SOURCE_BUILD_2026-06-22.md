# Native Init V3033 DOOMGENERIC Visible Loop Source Build

## Summary

- Cycle: `V3033`
- Track: active Video playback / DOOM capstone.
- Decision: `v3033-doomgeneric-visible-loop-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Device action: `none` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3033_doomgeneric_visible_loop.img`
- Boot SHA256: `8fa375702a5023d9cc1f0811c310993a86f58154d658047b8edbe44eece30a97`
- Init: `A90 Linux init 0.10.76 (v3033-doomgeneric-visible-loop)`

## Included Delta

- Extends the private doomgeneric helper with `--wad-frame-loop <path> --frames N --output <frame> --input-state <state> --frame-ms N`.
- Adds native-init `video demo doom loop [frames] --wad runtime-private --sha256 EXPECTED` for bounded foreground KMS presentation.
- Adds native-init `video demo doom loop-start [frames] --wad runtime-private --sha256 EXPECTED`, `loop-status`, and `loop-stop` for a background presenter that leaves the serial command path free for host keyboard input.
- Mirrors every `doompad key` / `doompad reset` state into a temporary input-state file consumed by the helper's `DG_GetKey` queue.
- Adds `host_doompad_keyboard_v3033.py`, which maps a host terminal keyboard to `doompad key <role> <0|1>` over `a90ctl.py` with all-up cleanup.
- The DEMO > DOOM menu item now launches a bounded visible playable loop and restores the menu afterward.

## Runtime WAD Contract

- Runtime WAD root: `/mnt/sdext/a90/runtime/doom/v3028/`
- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Runtime WAD max bytes: `67108864`
- WAD files in ramdisk: `0`
- Public WAD files committed/present: `0`
- WAD bytes embedded in boot image: `0`

## Loop Contract

- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3033 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 90 --output /tmp/a90-doomgeneric-v3033-loop-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3033-input.state --frame-ms 50`
- Native foreground command: `video demo doom loop 90 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Native background command: `video demo doom loop-start 300 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Host keyboard bridge: `workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py`
- Input state path: `/tmp/a90-doomgeneric-v3033-input.state`
- Frame path: `/tmp/a90-doomgeneric-v3033-loop-frame.xbgr8888`
- Frame format: `xbgr8888-raw`
- Frame geometry: `640x400` stride `2560` bytes `1024000`
- Default loop frames: `90`
- Loop frame ms: `50`

## Private Engine Helper

- Bundled helper path: `/bin/a90_doomgeneric_private_engine_v3033`
- V3033 engine binary: `workspace/private/builds/native-init/v3033-doomgeneric-visible-loop/a90_doomgeneric_private_engine_v3033`
- V3033 engine SHA256: `f33b0e1093a778d1081ded3e93503541f4c8269ae886c1fe4a8c36990bef3f8a`
- V3033 engine bytes: `1070008`
- Helper bundled in ramdisk: `1`

## Marker Check

- `A90 Linux init 0.10.76 (v3033-doomgeneric-visible-loop)`
- `v3033-doomgeneric-visible-loop`
- `doomgeneric-private-link-v3033-visible-loop`
- `/bin/a90_doomgeneric_private_engine_v3033`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3033-loop-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3033-input.state`
- `--wad-smoke`
- `--wad-frame-dump`
- `--wad-frame-loop`
- `--input-state`
- `--frame-ms`
- `a90.doomgeneric.v3033.visible_loop=state-file-frame-loop`
- `video demo doom loop [frames] --wad runtime-private --sha256`
- `video demo doom loop-start [frames] --wad runtime-private --sha256`
- `video.demo.doom.loop=doomgeneric-sd-wad-visible-playable-loop`
- `video.demo.doom.loop_start=background-presenter`
- `doompad.input_state.path=`
- `host_doompad_keyboard_v3033.py`
- `menu.demo.doom.action=visible-playable-loop`
- `WAD PLAYABLE LOOP`
- `video.demo.asset.wad.embedded_in_boot=%d`
- `video.demo.input.otg_required=0`

## Safety

- No device action was performed by this builder.
- No flash, serial live command, Wi-Fi action, sysfs write, evdev injection, uinput, PMIC, regulator, backlight, GPIO, GDSC, or forbidden partition path is touched.
- WAD/IWAD bytes remain only on the runtime SD path and are not copied into public, ramdisk, boot image, reports, or generated source.
- The input-state and frame files are temporary runtime files under `/tmp`, not WAD copies.
- The generated boot image and helper are private/untracked. Public output is limited to source, tests, host keyboard tooling, and this metadata-only report.
- Rollback target remains `v2321-usb-clean-identity-rodata` for the next live unit.

## Host Validation

- `py_compile`: builder, host keyboard bridge, selector, and focused tests.
- `unittest`: V3033 visible-loop tests, host keyboard bridge tests, V3031 visible-frame tests, and selector tests.
- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3033 visible-loop commands, input-state path, SD WAD path/hash, host bridge marker, and bounded helper markers.
- Ramdisk inventory: helper path present and WAD file count is zero.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3034`
- Type: rollback-gated live validation of V3033 visible-loop candidate.
- Scope: flash only the exact V3033 boot image through `native_init_flash.py`, health-check, run foreground `video demo doom loop 8 --wad runtime-private --sha256 EXPECTED`, then run `loop-start` with the host keyboard bridge sending bounded `doompad` transitions, confirm presentation/input markers, stop the loop, and rollback to V2321.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3033-doomgeneric-visible-loop", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3033-visible-loop", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3033", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3033-loop-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3033-input.state", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=50`
- Candidate type: `doomgeneric-visible-loop-candidate`.
