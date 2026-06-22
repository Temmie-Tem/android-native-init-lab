# Native Init V3086 DOOMGENERIC Pageflip Cadence Source Build

## Summary

- Cycle: `V3086`
- Track: active Video playback / DOOM capstone cadence isolation.
- Decision: `v3086-doomgeneric-pageflip-cadence-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3086_doomgeneric_pageflip_cadence.img`
- Boot SHA256: `71c84e04f5ec9357393ebdc682f7095777d395173b22fb7323e591a5bdd4d0b5`
- Init: `A90 Linux init 0.10.100 (v3086-doomgeneric-pageflip-cadence)`

## Included Delta

- Keeps V3084 background serial-preserve, V3083 fast 3:2 large dashboard, V3081 shared-frame IPC, V3079 presenter-paced helper, timing probe, and UDP/NCM input.
- Changes only pageflip submit guard: `18ms` -> `0ms`.
- Purpose: isolate whether the V3085 30fps lock comes from the extra submit guard landing each frame on every other vblank.

## Cadence Contract

- Baseline pageflip min submit interval ms: `18`
- Candidate pageflip min submit interval ms: `0`
- Presenter poll ms: `4`
- Helper frame ms: `28`
- Frame scale: `3:2-minimal-fastscale`
- Scale path: `fast-3to2-rowcopy`
- Frame IPC: `shared-mmap-seq-copy`
- Shared frame path: `/tmp/a90-doomgeneric-v3086-shared-frame.bin`
- Pace socket: `/tmp/a90-doomgeneric-v3086-pace.sock`
- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3086 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 300 --output /tmp/a90-doomgeneric-v3086-raw-fallback-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3086-input.state --frame-ms 28 --input-socket /tmp/a90-doomgeneric-v3086-input.sock --pace-socket /tmp/a90-doomgeneric-v3086-pace.sock --shared-frame /tmp/a90-doomgeneric-v3086-shared-frame.bin --input-udp 30570`

## Runtime Contract

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`

## Marker Check

- `A90 Linux init 0.10.100 (v3086-doomgeneric-pageflip-cadence)`
- `v3086-doomgeneric-pageflip-cadence`
- `doomgeneric-private-link-v3086-pageflip-cadence`
- `/bin/a90_doomgeneric_private_engine_v3086`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3086-raw-fallback-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3086-shared-frame.bin`
- `/tmp/a90-doomgeneric-v3086-input.state`
- `/tmp/a90-doomgeneric-v3086-input.sock`
- `/tmp/a90-doomgeneric-v3086-pace.sock`
- `a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback`
- `a90.doomgeneric.v3079.pace=presenter-pageflip-token`
- `a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq`
- `--shared-frame`
- `shared-mmap-copy`
- `video.demo.doom.presenter.pageflip_min_submit_interval_ms=%d`
- `video.demo.doom.dashboard.scale_path=fast-3to2-rowcopy`
- `video.demo.doom.loop_start.background_cancel=disabled-serial-preserve`
- `video.demo.doom.loop.frame_ipc=`
- `video.demo.doom.loop.timing_probe=1`
- `native-audio-corun-tone-v3053`

## Validation

- `py_compile`: V3086 builder and focused tests.
- `unittest`: V3086 source contract plus V3084/V3083/V3081/V3079/V3077/V3074/V3071 lineage regressions.
- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3086 identity, serial-preserve marker, fast-scale marker, shared-frame markers, pace/pageflip markers, timing telemetry, and UDP input markers.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3087`
- Type: rollback-gated live validation.
- Scope: flash exact V3086 boot image via `native_init_flash.py`, health-check, require pageflip min submit interval `0`, run bounded timing loop, compare flip delta distribution with V3085, and confirm background serial preserve still holds.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3086-doomgeneric-pageflip-cadence", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3086-pageflip-cadence", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3086", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3086-raw-fallback-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3086-input.state", -DA90_DOOMGENERIC_BRIDGE_INPUT="udp-ncm-to-DG_GetKey-with-serial-doompad-fallback", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=28, -DVIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS=4, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=10000, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=80, -DVIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER=1, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES=30, -DVIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_MINIMAL=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME=1, -DVIDEO_DEMO_DOOMGENERIC_PRESENT_PAGEFLIP=1, -DA90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH="/tmp/a90-doomgeneric-v3086-input.sock", -DA90_DOOMGENERIC_BRIDGE_SHARED_FRAME_PATH="/tmp/a90-doomgeneric-v3086-shared-frame.bin", -DA90_DOOMGENERIC_BRIDGE_PACE_SOCKET_PATH="/tmp/a90-doomgeneric-v3086-pace.sock", -DA90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT=30570`
- Candidate type: `doomgeneric-pageflip-cadence-candidate`.
