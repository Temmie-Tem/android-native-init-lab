# Native Init V3049 DOOMGENERIC Autostart Clear Source Build

## Summary

- Cycle: `V3049`
- Track: active Video playback / DOOM capstone.
- Decision: `v3049-doomgeneric-autostart-clear-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3049_doomgeneric_autostart_clear.img`
- Boot SHA256: `52609c265fc996d439c7979d400dce9213799a96eec3ed3aa77a2fa5c5ddfc53`
- Init: `A90 Linux init 0.10.83 (v3049-doomgeneric-autostart-clear)`

## Included Delta

- Keeps V3047 batch doompad input and V3045 continuous loop behavior.
- Adds helper argv autostart: `-warp 1 1 -skill 2`.
- Clears the KMS framebuffer on `video demo doom loop-stop`, including the inactive-loop case.
- Leaves DOOM sound unchanged for this unit: helper still uses `-nosound -nomusic`.

## Runtime Contract

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Frame path: `/tmp/a90-doomgeneric-v3049-autostart-clear-frame.xbgr8888`
- Input state path: `/tmp/a90-doomgeneric-v3049-input.state`
- Autostart marker: `a90.doomgeneric.v3049.autostart=warp-e1m1-skill2`
- Stop clear markers: `video.demo.doom.clear.reason=<reason>`, `video.demo.doom.clear.rc=<rc>`

## Marker Check

- `A90 Linux init 0.10.83 (v3049-doomgeneric-autostart-clear)`
- `v3049-doomgeneric-autostart-clear`
- `doomgeneric-private-link-v3049-autostart-clear`
- `/bin/a90_doomgeneric_private_engine_v3049`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3049-autostart-clear-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3049-input.state`
- `--wad-frame-loop`
- `--input-state`
- `--frame-ms`
- `a90.doomgeneric.v3045.continuous_loop=33ms-loop-start-zero-continuous`
- `a90.doomgeneric.v3045.loop=input-state-file-to-DG_GetKey-33ms-continuous`
- `a90.doomgeneric.v3045.frame_color=rb-swap-to-xbgr8888`
- `a90.doomgeneric.v3045.loop_frames_zero=continuous`
- `a90.doomgeneric.v3049.autostart=warp-e1m1-skill2`
- `-warp`
- `-skill`
- `doompad.batch=state-mask-v3047`
- `doompad.state_batch seq=`
- `doompad state <seq> <mask>`
- `video.demo.doom.clear.reason=`
- `video.demo.doom.clear.rc=`
- `video.demo.doom.loop_start.continuous`
- `video.demo.doom.loop_status.continuous`
- `video.demo.doom.dashboard.native=1`
- `video.demo.doom.dashboard.presenter_log=quiet-per-frame`
- `host_doompad_dashboard_v3035.py`
- `host_doompad_keyboard_v3033.py`
- `video.demo.input.otg_required=0`

## Validation

- `py_compile`: builder and focused tests.
- `unittest`: V3049 source contract plus V3045/V3047 regressions.
- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3049 autostart, clear, batch-input, and continuous-loop markers.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3050`
- Type: rollback-gated live validation of V3049 autostart/clear candidate.
- Scope: flash exact V3049 boot image, health-check, verify DOOM enters gameplay without remaining at the menu, verify `loop-stop` clears the screen, and keep DOOM sound parked as separate backend work.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3049-doomgeneric-autostart-clear", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3049-autostart-clear", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3049", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3049-autostart-clear-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3049-input.state", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=33, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME=1`
- Candidate type: `doomgeneric-autostart-clear-candidate`.
