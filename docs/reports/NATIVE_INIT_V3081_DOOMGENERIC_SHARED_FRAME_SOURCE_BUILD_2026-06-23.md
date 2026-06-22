# Native Init V3081 DOOMGENERIC Shared Frame Source Build

## Summary

- Cycle: `V3081`
- Track: active Video playback / DOOM capstone frame IPC.
- Decision: `v3081-doomgeneric-shared-frame-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3081_doomgeneric_shared_frame.img`
- Boot SHA256: `f632711c57bdab2114c02a330af3125e71df0d538692b99a304c68ba32fd2150`
- Init: `A90 Linux init 0.10.97 (v3081-doomgeneric-shared-frame)`

## Included Delta

- Keeps V3079 presenter-paced helper, pageflip presentation, minimal dashboard, timing probe, frame_ms=28, and UDP/NCM input.
- Adds a helper-created shared mmap frame file with a 64-byte header and even/odd sequence guard.
- Presenter reads the shared frame via mmap and copies only a stable sequence, avoiding per-frame raw-file open/read and helper write/rename.
- Leaves the raw frame file path compiled as fallback when no shared-frame path is configured.

## IPC Contract

- Baseline frame IPC: `raw-frame-file-rename-open-read`
- Candidate frame IPC: `shared-mmap-seq-copy`
- Shared frame path: `/tmp/a90-doomgeneric-v3081-shared-frame.bin`
- Raw fallback frame path: `/tmp/a90-doomgeneric-v3081-raw-fallback-frame.xbgr8888`
- Pace socket: `/tmp/a90-doomgeneric-v3081-pace.sock`
- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3081 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 300 --output /tmp/a90-doomgeneric-v3081-raw-fallback-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3081-input.state --frame-ms 28 --input-socket /tmp/a90-doomgeneric-v3081-input.sock --pace-socket /tmp/a90-doomgeneric-v3081-pace.sock --shared-frame /tmp/a90-doomgeneric-v3081-shared-frame.bin --input-udp 30570`
- Header: magic/version/header_bytes/geometry/sequence/frame_id, then XBGR8888 pixels.
- Sequence: odd means writer in progress; even nonzero means stable frame.

## Runtime Contract

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`

## Marker Check

- `A90 Linux init 0.10.97 (v3081-doomgeneric-shared-frame)`
- `v3081-doomgeneric-shared-frame`
- `doomgeneric-private-link-v3081-shared-frame`
- `/bin/a90_doomgeneric_private_engine_v3081`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3081-raw-fallback-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3081-shared-frame.bin`
- `/tmp/a90-doomgeneric-v3081-input.state`
- `/tmp/a90-doomgeneric-v3081-input.sock`
- `/tmp/a90-doomgeneric-v3081-pace.sock`
- `a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback`
- `a90.doomgeneric.v3079.pace=presenter-pageflip-token`
- `a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq`
- `--shared-frame`
- `shared-mmap-seq`
- `shared-mmap-copy`
- `video.demo.doom.frame.ipc=`
- `video.demo.doom.loop.frame_ipc=`
- `video.demo.doom.presenter.reader=`
- `video.demo.doom.loop.timing_probe=1`
- `pace_socket.tokens_sent=`
- `native-audio-corun-tone-v3053`

## Validation

- `py_compile`: V3081 builder and focused tests.
- `unittest`: V3081 source contract plus V3079/V3077/V3074/V3071 lineage regressions.
- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3081 identity, shared-frame helper markers, presenter shared-mmap markers, V3079 pace markers, pageflip telemetry, and UDP input markers.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3082`
- Type: rollback-gated live validation of V3081 shared-frame candidate.
- Scope: flash exact V3081 boot image via `native_init_flash.py`, health-check, require shared-frame markers, run bounded foreground timing loop, compare read/copy and flip delta distribution with V3080, then verify continuous loop and UDP input.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3081-doomgeneric-shared-frame", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3081-shared-frame", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3081", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3081-raw-fallback-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3081-input.state", -DA90_DOOMGENERIC_BRIDGE_INPUT="udp-ncm-to-DG_GetKey-with-serial-doompad-fallback", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=28, -DVIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS=4, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=10000, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=80, -DVIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER=1, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES=30, -DVIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_MINIMAL=1, -DVIDEO_DEMO_DOOMGENERIC_PRESENT_PAGEFLIP=1, -DVIDEO_DEMO_DOOMGENERIC_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS=18, -DA90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH="/tmp/a90-doomgeneric-v3081-input.sock", -DA90_DOOMGENERIC_BRIDGE_SHARED_FRAME_PATH="/tmp/a90-doomgeneric-v3081-shared-frame.bin", -DA90_DOOMGENERIC_BRIDGE_PACE_SOCKET_PATH="/tmp/a90-doomgeneric-v3081-pace.sock", -DA90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT=30570`
- Candidate type: `doomgeneric-shared-frame-candidate`.
