# Native Init V3040 DOOMGENERIC Large Dashboard Quiet Source Build

## Summary

- Cycle: `V3040`
- Track: active Video playback / DOOM capstone.
- Decision: `v3040-doomgeneric-large-dashboard-quiet-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Device action: `none` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3040_doomgeneric_large_dashboard_quiet.img`
- Boot SHA256: `d9674661639897b1e0bb94c293b1193fbefb8cfab38047505381d23cba77b686`
- Init: `A90 Linux init 0.10.79 (v3040-doomgeneric-large-dashboard-quiet)`

## Included Delta

- Keeps the V3038 large `960x600` DOOM frame and overlay title layout.
- Keeps the runtime-private WAD, private doomgeneric helper, native dashboard, and serial doompad input-state bridge.
- Changes the active `doomdash` KMS presenter to quiet per-frame serial output with `a90_kms_present("doomdash", false)`.
- Adds `video.demo.doom.dashboard.presenter_log=quiet-per-frame` as the status marker.
- Host input remains serial-only through `doompad key <role> <0|1>`; no OTG keyboard, evdev injection, uinput, or host USB HID injection is introduced.

## Runtime WAD Contract

- Runtime WAD root: `/mnt/sdext/a90/runtime/doom/v3028/`
- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Runtime WAD max bytes: `67108864`
- WAD files in ramdisk: `0`
- Public WAD files committed/present: `0`
- WAD bytes embedded in boot image: `0`

## Dashboard Contract

- Native dashboard flag: `A90_DOOMGENERIC_NATIVE_DASHBOARD=1`
- Large-frame flag: `A90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME=1`
- Presenter log marker: `video.demo.doom.dashboard.presenter_log=quiet-per-frame`
- Frame mode marker: `video.demo.doom.dashboard.frame_mode=large-overlay-title`
- Frame scale marker: `video.demo.doom.dashboard.frame_scale=3:2`
- Rendered frame size: `960x600` from `640x400`
- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3040 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 300 --output /tmp/a90-doomgeneric-v3040-large-dashboard-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3040-input.state --frame-ms 50`
- Native background command: `video demo doom loop-start 300 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Host dashboard: `workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py`
- Host keyboard bridge: `workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py`
- Input state path: `/tmp/a90-doomgeneric-v3040-input.state`
- Frame path: `/tmp/a90-doomgeneric-v3040-large-dashboard-frame.xbgr8888`
- Loop frame ms: `50`

## Private Engine Helper

- Bundled helper path: `/bin/a90_doomgeneric_private_engine_v3040`
- V3040 engine binary: `workspace/private/builds/native-init/v3040-doomgeneric-large-dashboard-quiet/a90_doomgeneric_private_engine_v3040`
- V3040 engine SHA256: `30969d3873d1ee33eddd8d3aad95bc6bbeac7333c148a41eb2ef6ce375d07fde`
- V3040 engine bytes: `1070008`
- Helper bundled in ramdisk: `1`

## Marker Check

- `A90 Linux init 0.10.79 (v3040-doomgeneric-large-dashboard-quiet)`
- `v3040-doomgeneric-large-dashboard-quiet`
- `doomgeneric-private-link-v3040-large-dashboard-quiet`
- `/bin/a90_doomgeneric_private_engine_v3040`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3040-large-dashboard-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3040-input.state`
- `--wad-frame-loop`
- `--input-state`
- `--frame-ms`
- `a90.doomgeneric.v3040.large_dashboard_quiet=state-file-frame-loop-kms-large-overlay-title-quiet-present`
- `a90.doomgeneric.v3040.loop=input-state-file-to-DG_GetKey`
- `video.demo.doom.dashboard.native=1`
- `video.demo.doom.dashboard.layout=top-frame-metrics-logs-input`
- `video.demo.doom.dashboard.presenter_log=quiet-per-frame`
- `video.demo.doom.dashboard.large_frame=1`
- `video.demo.doom.dashboard.frame_mode=large-overlay-title`
- `video.demo.doom.dashboard.frame_scale=3:2`
- `DOOM LIVE DASHBOARD`
- `KEYBOARD / DOOMPAD INPUT`
- `640x400 -> 960x600`
- `host_doompad_dashboard_v3035.py`
- `host_doompad_keyboard_v3033.py`
- `video demo doom loop-start [frames] --wad runtime-private --sha256`
- `video.demo.doom.loop_start=background-presenter`
- `video.demo.input.otg_required=0`

## Safety

- No device action was performed by this builder.
- No flash, serial live command, Wi-Fi action, sysfs write, evdev injection, uinput, PMIC, regulator, backlight, GPIO, GDSC, or forbidden partition path is touched.
- WAD/IWAD bytes remain only on the runtime SD path and are not copied into public, ramdisk, boot image, reports, or generated source.
- The generated boot image and helper are private/untracked. Public output is limited to source, tests, host tooling, and this metadata-only report.
- Rollback target remains `v2321-usb-clean-identity-rodata` for the next live unit.

## Host Validation

- `py_compile`: builder, dependent host scripts, and focused tests.
- `unittest`: V3040 quiet-dashboard tests plus V3038/V3036/V3035/V3033 regression tests.
- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3040 quiet-dashboard markers, helper path, input-state path, SD WAD path/hash, host dashboard marker, and bounded loop command markers.
- Ramdisk inventory: helper path present and WAD file count is zero.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3041`
- Type: rollback-gated live validation of V3040 quiet large-dashboard candidate.
- Scope: flash only the exact V3040 boot image through `native_init_flash.py`, health-check, run `video demo doom loop-start 300 --wad runtime-private --sha256 EXPECTED`, confirm quiet-presenter markers, drive bounded doompad transitions while active loop is running, stop the loop, and leave candidate installed only if health and validation pass.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3040-doomgeneric-large-dashboard-quiet", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3040-large-dashboard-quiet", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3040", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3040-large-dashboard-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3040-input.state", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=50, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME=1`
- Candidate type: `doomgeneric-large-dashboard-quiet-candidate`.
