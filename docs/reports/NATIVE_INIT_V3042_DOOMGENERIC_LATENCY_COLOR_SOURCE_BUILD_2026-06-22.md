# Native Init V3042 DOOMGENERIC Latency Color Source Build

## Summary

- Cycle: `V3042`
- Track: active Video playback / DOOM capstone.
- Decision: `v3042-doomgeneric-latency-color-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Device action: `none` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3042_doomgeneric_latency_color.img`
- Boot SHA256: `a6501a945876daf11d2dc5215d3c607706a10db37c5a2657092a0a5280c2c66c`
- Init: `A90 Linux init 0.10.80 (v3042-doomgeneric-latency-color)`

## Included Delta

- Keeps the V3040 large native dashboard and quiet per-frame presenter.
- Reduces the helper/presenter loop cadence from `50ms` to `33ms` for the DOOM loop.
- Converts the doomgeneric frame buffer from observed red/blue-swapped order into the declared `xbgr8888` raw frame before writing the temporary frame file.
- Keeps host input serial-only through `doompad key <role> <0|1>`; no OTG keyboard, evdev injection, uinput, or host USB HID injection is introduced.

## Latency / Color Contract

- Helper color marker: `a90.doomgeneric.v3042.frame_color=rb-swap-to-xbgr8888`
- Loop marker: `a90.doomgeneric.v3042.loop=input-state-file-to-DG_GetKey-33ms`
- Candidate marker: `a90.doomgeneric.v3042.latency_color=33ms-loop-rb-swap-xbgr8888`
- Helper loop frame ms: `33`
- Frame path: `/tmp/a90-doomgeneric-v3042-latency-color-frame.xbgr8888`
- Input state path: `/tmp/a90-doomgeneric-v3042-input.state`
- Raw frame geometry: `640x400` stride `2560` bytes `1024000`

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
- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3042 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 300 --output /tmp/a90-doomgeneric-v3042-latency-color-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3042-input.state --frame-ms 33`
- Native background command: `video demo doom loop-start 300 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Host dashboard: `workspace/public/src/scripts/revalidation/host_doompad_dashboard_v3035.py`
- Host keyboard bridge: `workspace/public/src/scripts/revalidation/host_doompad_keyboard_v3033.py`

## Private Engine Helper

- Bundled helper path: `/bin/a90_doomgeneric_private_engine_v3042`
- V3042 engine binary: `workspace/private/builds/native-init/v3042-doomgeneric-latency-color/a90_doomgeneric_private_engine_v3042`
- V3042 engine SHA256: `4a6c96ac8d7bdf6609726c542f5089454f20c2bc3f918f35f0abf7d9df1654f2`
- V3042 engine bytes: `1070008`
- Helper bundled in ramdisk: `1`

## Marker Check

- `A90 Linux init 0.10.80 (v3042-doomgeneric-latency-color)`
- `v3042-doomgeneric-latency-color`
- `doomgeneric-private-link-v3042-latency-color`
- `/bin/a90_doomgeneric_private_engine_v3042`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3042-latency-color-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3042-input.state`
- `--wad-frame-loop`
- `--input-state`
- `--frame-ms`
- `a90.doomgeneric.v3042.latency_color=33ms-loop-rb-swap-xbgr8888`
- `a90.doomgeneric.v3042.loop=input-state-file-to-DG_GetKey-33ms`
- `a90.doomgeneric.v3042.frame_color=rb-swap-to-xbgr8888`
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
- `unittest`: V3042 latency/color tests plus host fast-path tests and V3040/V3038 dashboard regressions.
- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3042 latency/color markers, helper path, input-state path, SD WAD path/hash, host dashboard marker, and bounded loop command markers.
- Ramdisk inventory: helper path present and WAD file count is zero.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3043`
- Type: rollback-gated live validation of V3042 latency/color candidate.
- Scope: flash only the exact V3042 boot image through `native_init_flash.py`, health-check, run `video demo doom loop-start 300 --wad runtime-private --sha256 EXPECTED`, confirm 33ms/status markers, drive bounded doompad transitions through the host fast path, visually verify R/B channel correction, stop the loop, and leave candidate installed only if health and validation pass.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3042-doomgeneric-latency-color", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3042-latency-color", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3042", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3042-latency-color-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3042-input.state", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=33, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME=1`
- Candidate type: `doomgeneric-latency-color-candidate`.
