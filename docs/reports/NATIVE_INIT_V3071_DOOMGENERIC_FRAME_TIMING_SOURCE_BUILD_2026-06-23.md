# Native Init V3071 DOOMGENERIC Frame Timing Source Build

## Summary

- Cycle: `V3071`
- Track: active Video playback / DOOM capstone frame pacing.
- Decision: `v3071-doomgeneric-frame-timing-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3071_doomgeneric_frame_timing.img`
- Boot SHA256: `6c26f341453b505aab85cba76caee6ab1aefe69d702f37d4370baf78da6e5a29`
- Init: `A90 Linux init 0.10.93 (v3071-doomgeneric-frame-timing)`

## Included Delta

- Keeps V3069 metrics cache, V3067 reader-buffer reuse, V3065 large-scale-off, V3063 frame_ms=28, and UDP/NCM input unchanged.
- Adds a DOOM presenter timing probe that separates allocation, frame-file read, KMS begin, dashboard/blit draw, and KMS present costs.
- This targets the post-V3070 uncertainty between raw frame-file IPC and DRM atomic commit/present stalls.

## Timing Contract

- Baseline frame timing probe: `0`
- Candidate frame timing probe: `1`
- Timing marker: `frame-ipc-kms-stage-us`
- Dashboard metrics interval frames: `30`
- Dashboard metrics pacing marker: `cached-frame-interval`
- Reader reuse: `1`
- Helper frame ms: `28`
- Presenter poll ms: `4`
- Dashboard large frame: `0`
- Frame path: `/tmp/a90-doomgeneric-v3071-frame-timing-frame.xbgr8888`

## Runtime Contract

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3071 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 300 --output /tmp/a90-doomgeneric-v3071-frame-timing-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3071-input.state --frame-ms 28 --input-socket /tmp/a90-doomgeneric-v3071-input.sock --input-udp 30570`

## Marker Check

- `A90 Linux init 0.10.93 (v3071-doomgeneric-frame-timing)`
- `v3071-doomgeneric-frame-timing`
- `doomgeneric-private-link-v3071-frame-timing`
- `/bin/a90_doomgeneric_private_engine_v3071`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3071-frame-timing-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3071-input.state`
- `/tmp/a90-doomgeneric-v3071-input.sock`
- `a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback`
- `--input-udp`
- `udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`
- `video.demo.doom.loop.frame_ms=`
- `video.demo.doom.presenter.pacing=helper-frame-mtime`
- `video.demo.doom.presenter.reader=reused-loop-buffer`
- `video.demo.doom.presenter.buffer_reuse=1`
- `video.demo.doom.dashboard.metrics_interval_frames=`
- `video.demo.doom.dashboard.metrics_pacing=cached-frame-interval`
- `video.demo.doom.loop.timing_probe=1`
- `video.demo.doom.loop.timing=frame-ipc-kms-stage-us`
- `timing.read`
- `timing.present`
- `avg_us`
- `max_us`
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

- `py_compile`: V3071 builder and focused tests.
- `unittest`: V3071 source contract plus V3069/V3067/V3065/V3063/V3061/V3059 and base visible-loop regressions.
- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3071 identity, timing probe, reader reuse, dashboard metrics cache, and UDP input markers.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3072`
- Type: rollback-gated live validation of V3071 frame-timing candidate.
- Scope: flash exact V3071 boot image via `native_init_flash.py`, health-check, run a bounded foreground DOOM loop, capture timing averages/maxima, then start continuous loop and verify UDP input still works.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3071-doomgeneric-frame-timing", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3071-frame-timing", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3071", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3071-frame-timing-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3071-input.state", -DA90_DOOMGENERIC_BRIDGE_INPUT="udp-ncm-to-DG_GetKey-with-serial-doompad-fallback", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=28, -DVIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS=4, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=10000, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=80, -DVIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER=1, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES=30, -DVIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH="/tmp/a90-doomgeneric-v3071-input.sock", -DA90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT=30570`
- Candidate type: `doomgeneric-frame-timing-candidate`.
