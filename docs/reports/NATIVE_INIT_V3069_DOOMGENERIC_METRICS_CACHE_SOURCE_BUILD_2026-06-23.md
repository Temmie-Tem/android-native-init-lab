# Native Init V3069 DOOMGENERIC Metrics Cache Source Build

## Summary

- Cycle: `V3069`
- Track: active Video playback / DOOM capstone frame pacing.
- Decision: `v3069-doomgeneric-metrics-cache-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3069_doomgeneric_metrics_cache.img`
- Boot SHA256: `660bf97fcb43df419c1ecc8eef20a127f2be1bb88180340eb4bc63e107e8acad`
- Init: `A90 Linux init 0.10.92 (v3069-doomgeneric-metrics-cache)`

## Included Delta

- Keeps V3067 reader-buffer reuse, V3065 large-scale-off, V3063 frame_ms=28, and UDP/NCM input unchanged.
- Changes native DOOM dashboard metrics from per-frame sysfs reads to cached reads every 30 presented frames.
- This targets the V3068 stack finding where presenter blocked in `wsa881x_get_temp` through thermal sysfs.

## Metrics Contract

- Baseline metrics interval frames: `1`
- Candidate metrics interval frames: `30`
- Metrics pacing marker: `cached-frame-interval`
- Reader reuse: `1`
- Helper frame ms: `28`
- Presenter poll ms: `4`
- Dashboard large frame: `0`
- Frame path: `/tmp/a90-doomgeneric-v3069-metrics-cache-frame.xbgr8888`

## Runtime Contract

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3069 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 300 --output /tmp/a90-doomgeneric-v3069-metrics-cache-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3069-input.state --frame-ms 28 --input-socket /tmp/a90-doomgeneric-v3069-input.sock --input-udp 30570`

## Marker Check

- `A90 Linux init 0.10.92 (v3069-doomgeneric-metrics-cache)`
- `v3069-doomgeneric-metrics-cache`
- `doomgeneric-private-link-v3069-metrics-cache`
- `/bin/a90_doomgeneric_private_engine_v3069`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3069-metrics-cache-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3069-input.state`
- `/tmp/a90-doomgeneric-v3069-input.sock`
- `a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback`
- `--input-udp`
- `udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`
- `video.demo.doom.loop.frame_ms=`
- `video.demo.doom.presenter.pacing=helper-frame-mtime`
- `video.demo.doom.presenter.reader=reused-loop-buffer`
- `video.demo.doom.presenter.buffer_reuse=1`
- `video.demo.doom.dashboard.metrics_interval_frames=`
- `video.demo.doom.dashboard.metrics_pacing=cached-frame-interval`
- `video.demo.doom.dashboard.native=1`
- `video.demo.doom.dashboard.large_frame=0`
- `video.demo.doom.dashboard.frame_scale=1:1`
- `video.demo.input.udp_port=`
- `video.demo.input.socket_path=`
- `video.demo.input.otg_required=0`
- `doompad.batch=state-mask-v3047`
- `video.demo.doom.loop_start.continuous`
- `native-audio-corun-tone-v3053`
- `host_doompad_keyboard_v3033.py`

## Validation

- `py_compile`: V3069 builder and focused tests.
- `unittest`: V3069 source contract plus V3067/V3065/V3063/V3061/V3059 and base visible-loop regressions.
- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3069 identity, reader reuse, dashboard metrics cache, and UDP input markers.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3070`
- Type: rollback-gated live validation of V3069 metrics-cache candidate.
- Scope: flash exact V3069 boot image via `native_init_flash.py`, health-check, require `video.demo.doom.dashboard.metrics_pacing=cached-frame-interval`, start continuous DOOM loop, and sample presenter state/stack after metrics throttling.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3069-doomgeneric-metrics-cache", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3069-metrics-cache", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3069", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3069-metrics-cache-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3069-input.state", -DA90_DOOMGENERIC_BRIDGE_INPUT="udp-ncm-to-DG_GetKey-with-serial-doompad-fallback", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=28, -DVIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS=4, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=10000, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=80, -DVIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER=1, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES=30, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH="/tmp/a90-doomgeneric-v3069-input.sock", -DA90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT=30570`
- Candidate type: `doomgeneric-metrics-cache-candidate`.
