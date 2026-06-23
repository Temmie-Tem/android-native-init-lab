# Native Init V3123 DOOMGENERIC Summary-Only Direct Blit Source Build

## Summary

- Cycle: `V3123`
- Track: DOOM frame IPC/copy reduction / validation-output decongestion.
- Decision: `v3123-doomgeneric-summary-only-direct-blit-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3123_doomgeneric_summary_only_direct_blit.img`
- Boot SHA256: `248af9a65bb9d4c30cd1c0cd11db642c1cbcb332697b0387372bd7465175b808`
- Init: `A90 Linux init 0.10.116 (v3123-doomgeneric-summary-only-direct-blit)`

## Included Delta

- Inherits V3120 direct shared-frame blit and V3118 no-full-clear pre-scaled producer behavior.
- Adds `VIDEO_DEMO_DOOMGENERIC_FOREGROUND_FRAME_LOG=0` for this candidate, so foreground loop validation still draws each frame but does not emit per-frame dashboard lines over serial.
- Adds loop-start summary markers for dashboard scale/no-full-clear/direct-reader state, preserving the evidence needed by live validation without flooding ACM output.

## Runtime Contract

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3123 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 300 --output /tmp/a90-doomgeneric-v3123-raw-fallback-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3123-input.state --frame-ms 28 --input-socket /tmp/a90-doomgeneric-v3123-input.sock --pace-socket /tmp/a90-doomgeneric-v3123-pace.sock --shared-frame /tmp/a90-doomgeneric-v3123-shared-frame.bin --input-udp 30570`
- Frame geometry: `960x600` stride `3840` bytes `2304000`
- Frame IPC: `shared-mmap-direct-blit-summary-only`
- Scale path: `producer-pre-scaled-raw-rowcopy`
- Clear path: `dirty-dashboard-regions`
- Expected live markers: `video.demo.doom.loop.presenter.reader=shared-mmap-direct-blit` and `video.demo.doom.loop.foreground_frame_log=0`.

## Safety

- Boot partition only through the checked flash helper `native_init_flash.py` in the next live unit.
- No GPU/GL stack, panel re-init, backlight, PMIC, regulator, GDSC, GPIO, Wi-Fi connect/dhcp/ping, or forbidden partition path.
- This source build only changes serial validation verbosity and keeps the userspace presenter read/blit path additive.

## Validation

- `py_compile`: V3123 builder and focused tests.
- `unittest`: V3123 source contract plus V3122/V3120/V3119 regressions.
- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3123 identity, direct-shared-blit reader marker, summary-only foreground marker, pre-scaled/no-full-clear markers, shared-frame/pageflip/input/audio markers, and no HW-plane atomic requirement.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3124`
- Type: rollback-gated live validation.
- Scope: flash exact V3123 image, require summary-only and direct-shared-blit markers, compare `timing.read.avg_us`, `timing.draw.avg_us`, and pageflip cadence against V3119/V3122.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3123-doomgeneric-summary-only-direct-blit", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3123-summary-only-direct-blit", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3123", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3123-raw-fallback-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3123-input.state", -DA90_DOOMGENERIC_BRIDGE_INPUT="udp-ncm-to-DG_GetKey-with-serial-doompad-fallback", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=960, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=600, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=3840, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=2304000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=28, -DVIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS=4, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=10000, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=80, -DVIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER=1, -DVIDEO_DEMO_DOOMGENERIC_DIRECT_SHARED_BLIT=1, -DVIDEO_DEMO_DOOMGENERIC_FOREGROUND_FRAME_LOG=0, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES=30, -DVIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE=1, -DVIDEO_DEMO_DOOMGENERIC_SEQ_TELEMETRY=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_MINIMAL=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME=1, -DVIDEO_DEMO_DOOMGENERIC_PRE_SCALED_LARGE_FRAME=1, -DVIDEO_DEMO_DOOMGENERIC_NO_FULL_CLEAR=1, -DVIDEO_DEMO_DOOMGENERIC_PRESENT_PAGEFLIP=1, -DA90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH="/tmp/a90-doomgeneric-v3123-input.sock", -DA90_DOOMGENERIC_BRIDGE_SHARED_FRAME_PATH="/tmp/a90-doomgeneric-v3123-shared-frame.bin", -DA90_DOOMGENERIC_BRIDGE_PACE_SOCKET_PATH="/tmp/a90-doomgeneric-v3123-pace.sock", -DA90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT=30570`
- Candidate type: `doomgeneric-summary-only-direct-blit-candidate`.
