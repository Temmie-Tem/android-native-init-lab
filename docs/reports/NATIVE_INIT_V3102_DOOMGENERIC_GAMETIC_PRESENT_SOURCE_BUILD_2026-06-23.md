# Native Init V3102 DOOMGENERIC Gametic Present Source Build

## Summary

- Cycle: `V3102`
- Track: active Video playback / DOOM tic cadence behavior.
- Decision: `v3102-doomgeneric-gametic-present-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3102_doomgeneric_gametic_present.img`
- Boot SHA256: `79c32a132ff69871b84482e432ac6127c717a8fb3764484a863326575e1c91a1`
- Init: `A90 Linux init 0.10.107 (v3102-doomgeneric-gametic-present)`

## Included Delta

- Keeps V3100's 1:1 scale, shared-frame sequence telemetry, tick/draw/dump phase telemetry, pageflip path, audio corun, and UDP/NCM input.
- Changes helper frame publication to emit only when `gametic` changes; repeated-gametic draws are skipped instead of publishing a new shared-frame sequence.
- Changes presenter pacing for this mode so idle polls can send bounded tick tokens; this avoids deadlock when no new frame is published.
- Tick token interval: `14286us`, targeting roughly 70 helper ticks/s so the 35 Hz DOOM tic cadence can be observed without repeated-frame presentation.

## Telemetry Contract

- Tick telemetry marker: `a90.doomgeneric.v3102.tick_telemetry=gametic-present-phase-summary`
- Phase telemetry marker: `a90.doomgeneric.v3102.phase_telemetry=tick-draw-dump-split`
- Gametic-present marker: `a90.doomgeneric.v3102.gametic_present=changed-gametic-only`
- Telemetry path: `/tmp/a90-doomgeneric-v3102-tick-telemetry.txt`
- Key fields: `loop_tick.*`, `draw_gametic.*`, `dump_gametic.*`, `dump_gametic.emitted_changed_only`, `dump_gametic.skipped_same_gametic`, and `pace_socket.idle_tokens_sent`.

## Runtime Contract

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3102 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 300 --output /tmp/a90-doomgeneric-v3102-raw-fallback-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3102-input.state --frame-ms 28 --input-socket /tmp/a90-doomgeneric-v3102-input.sock --pace-socket /tmp/a90-doomgeneric-v3102-pace.sock --shared-frame /tmp/a90-doomgeneric-v3102-shared-frame.bin --input-udp 30570`
- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`

## Marker Check

- `A90 Linux init 0.10.107 (v3102-doomgeneric-gametic-present)`
- `v3102-doomgeneric-gametic-present`
- `doomgeneric-private-link-v3102-gametic-present`
- `/bin/a90_doomgeneric_private_engine_v3102`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3102-raw-fallback-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3102-shared-frame.bin`
- `/tmp/a90-doomgeneric-v3102-input.state`
- `/tmp/a90-doomgeneric-v3102-input.sock`
- `/tmp/a90-doomgeneric-v3102-pace.sock`
- `/tmp/a90-doomgeneric-v3102-tick-telemetry.txt`
- `a90.doomgeneric.v3102.tick_telemetry=gametic-present-phase-summary`
- `a90.doomgeneric.v3102.scale=large-frame-off-1to1`
- `a90.doomgeneric.v3102.gametic_frame_telemetry=changed-only-dump-summary`
- `a90.doomgeneric.v3102.phase_telemetry=tick-draw-dump-split`
- `a90.doomgeneric.v3102.gametic_present=changed-gametic-only`
- `video.demo.doom.presenter.gametic_present_only=%d`
- `video.demo.doom.presenter.tick_pace_interval_us=%u`
- `video.demo.doom.loop.presenter.gametic_present_only=%d`
- `video.demo.doom.loop.pace_socket.idle_tokens_sent=%u`
- `dump_gametic.emitted_changed_only=%u`
- `dump_gametic.skipped_same_gametic=%u`
- `gametic_present_only=changed-gametic-only`
- `a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback`
- `a90.doomgeneric.v3079.pace=presenter-pageflip-token`
- `a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq`
- `--shared-frame`
- `shared-mmap-copy`
- `video.demo.doom.dashboard.large_frame=0`
- `video.demo.doom.dashboard.frame_scale=1:1`
- `video.demo.doom.loop.seq_telemetry=1`
- `frame-id-upper32-shared-seq`
- `loop_tick.samples=%u`
- `draw_gametic.samples=%u`
- `dump_gametic.samples=%u`
- `video.demo.doom.loop_start.background_cancel=disabled-serial-preserve`
- `video.demo.doom.loop.timing_probe=1`
- `native-audio-corun-tone-v3053`

## Validation

- `py_compile`: V3102 builder and focused tests.
- `unittest`: V3102 source contract plus current DOOM cadence lineage regressions.
- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3102 identity, changed-gametic presentation markers, idle pace-token markers, phase telemetry markers, 1:1 scale marker, sequence telemetry markers, shared-frame markers, audio marker, and UDP input markers.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3103`
- Type: rollback-gated live validation.
- Scope: flash exact V3102 boot image via `native_init_flash.py`, health-check, run bounded DOOM loops, and compare `frames_presented`, `dump_gametic.*`, pageflip deltas, and idle pace-token counts against V3101.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3102-doomgeneric-gametic-present", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3102-gametic-present", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3102", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3102-raw-fallback-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3102-input.state", -DA90_DOOMGENERIC_BRIDGE_INPUT="udp-ncm-to-DG_GetKey-with-serial-doompad-fallback", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=28, -DVIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS=4, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=10000, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=80, -DVIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER=1, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES=30, -DVIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE=1, -DVIDEO_DEMO_DOOMGENERIC_SEQ_TELEMETRY=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_MINIMAL=1, -DVIDEO_DEMO_DOOMGENERIC_PRESENT_PAGEFLIP=1, -DVIDEO_DEMO_DOOMGENERIC_GAMETIC_PRESENT_ONLY=1, -DVIDEO_DEMO_DOOMGENERIC_TICK_PACE_INTERVAL_US=14286, -DA90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH="/tmp/a90-doomgeneric-v3102-input.sock", -DA90_DOOMGENERIC_BRIDGE_SHARED_FRAME_PATH="/tmp/a90-doomgeneric-v3102-shared-frame.bin", -DA90_DOOMGENERIC_BRIDGE_PACE_SOCKET_PATH="/tmp/a90-doomgeneric-v3102-pace.sock", -DA90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT=30570`
- Candidate type: `doomgeneric-gametic-present-candidate`.
