# Native Init V3108 DOOMGENERIC Hardware Plane Scale Source Build

## Summary

- Cycle: `V3108`
- Track: DOOM large-frame scale-path optimization.
- Decision: `v3108-doomgeneric-hw-plane-scale-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3108_doomgeneric_hw_plane_scale.img`
- Boot SHA256: `58affe427e1f9417f7c89f539528a3f693f5f38ae47ed3fae16124fc64055001`
- Init: `A90 Linux init 0.10.109 (v3108-doomgeneric-hw-plane-scale)`

## Included Delta

- Keeps the original DOOM cadence lineage from V3100 rather than the non-original-speed V3104 paced-tic diagnostic.
- Re-enables the 640x400 -> 960x600 large DOOM dashboard frame.
- Adds `VIDEO_DEMO_DOOMGENERIC_HW_PLANE_SCALE=1`: the presenter copies the raw 640x400 XBGR8888 frame into a small dumb buffer and asks DRM/SDE to scale it with plane source/destination rectangles.
- The software 3:2 fast row-copy scaler remains a fallback if no unused compatible plane can be attached.
- `loop-stop` clears the scaled plane before restoring the full-screen KMS path.

## Scale Contract

- V3107 plane probe: `candidate_count=16`, `active_source=current-plane`.
- Baseline frame scale: `1:1`
- Candidate frame scale: `3:2-hw-plane`
- Candidate scale path: `drm-plane-srcdst`
- Fallback scale path: `fast-3to2-rowcopy`
- Plane policy: use an unused compatible plane only; do not steal the current full-screen primary plane.
- Display mutation: bounded `DRM_IOCTL_MODE_SETPLANE` only, with full-screen KMS path retained.

## Runtime Contract

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Helper loop command: `/bin/a90_doomgeneric_private_engine_v3108 --wad-frame-loop /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 300 --output /tmp/a90-doomgeneric-v3108-raw-fallback-frame.xbgr8888 --input-state /tmp/a90-doomgeneric-v3108-input.state --frame-ms 28 --input-socket /tmp/a90-doomgeneric-v3108-input.sock --pace-socket /tmp/a90-doomgeneric-v3108-pace.sock --shared-frame /tmp/a90-doomgeneric-v3108-shared-frame.bin --input-udp 30570`
- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`

## Additional Cause Check

- If `hw_plane.presented=0`, the large path has fallen back to the CPU 3:2 row-copy scaler, so V3095's large-scaler stutter remains expected.
- If `hw_plane.presented=1` but the DOOM frame is not visible, suspect plane ordering/zpos or a legacy `SETPLANE` driver quirk; this source build records plane id/fb id/rc but live visual confirmation is still required.
- If pageflip stays near 16.6 ms and `seq.shared_missed_frames=0`, remaining stepped motion is the known DOOM 35 Hz game-tic cadence on the 60 Hz panel, not presenter jitter.
- Sound in this candidate is still `native-audio-corun-tone-v3053`, not real DOOM music/SFX; silence after the bounded tone duration is not evidence that DOOM audio is wired.

## Marker Check

- `A90 Linux init 0.10.109 (v3108-doomgeneric-hw-plane-scale)`
- `v3108-doomgeneric-hw-plane-scale`
- `doomgeneric-private-link-v3108-hw-plane-scale`
- `/bin/a90_doomgeneric_private_engine_v3108`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3108-raw-fallback-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3108-shared-frame.bin`
- `/tmp/a90-doomgeneric-v3108-input.state`
- `/tmp/a90-doomgeneric-v3108-input.sock`
- `/tmp/a90-doomgeneric-v3108-pace.sock`
- `/tmp/a90-doomgeneric-v3108-tick-telemetry.txt`
- `a90.doomgeneric.v3108.tick_telemetry=hw-plane-scale-original-cadence`
- `a90.doomgeneric.v3108.scale=drm-plane-srcdst-large`
- `a90.doomgeneric.v3108.phase_telemetry=tick-draw-dump-split`
- `a90.doomgeneric.v3108.gametic_frame_telemetry=loop-dump-gametic-summary`
- `a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback`
- `a90.doomgeneric.v3079.pace=presenter-pageflip-token`
- `a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq`
- `--shared-frame`
- `shared-mmap-copy`
- `video.demo.doom.dashboard.hw_plane_scale=1`
- `video.demo.doom.dashboard.frame_mode=minimal-large-hw-plane-scale`
- `video.demo.doom.dashboard.frame_scale=3:2`
- `video.demo.doom.dashboard.scale_path=drm-plane-srcdst`
- `video.demo.doom.dashboard.hw_plane.fallback=fast-3to2-rowcopy`
- `video.demo.doom.loop.seq_telemetry=1`
- `frame-id-upper32-shared-seq`
- `video.demo.doom.loop.timing_probe=1`
- `native-audio-corun-tone-v3053`

## Validation

- `py_compile`: V3108 builder and focused tests.
- `unittest`: V3108 source contract plus current KMS/DOOM scale-path checks.
- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3108 identity, hardware-plane scale markers, shared-frame/pageflip/input/audio markers, and original-cadence telemetry markers.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3109`
- Type: rollback-gated live validation.
- Scope: flash exact V3108 image via `native_init_flash.py`, health-check, run bounded large DOOM loop, require `hw_plane.presented=1` or record fallback, compare draw/total timing and pageflip deltas with V3095/V3101.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3108-doomgeneric-hw-plane-scale", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3108-hw-plane-scale", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3108", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3108-raw-fallback-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3108-input.state", -DA90_DOOMGENERIC_BRIDGE_INPUT="udp-ncm-to-DG_GetKey-with-serial-doompad-fallback", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=28, -DVIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS=4, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=10000, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=80, -DVIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER=1, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES=30, -DVIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE=1, -DVIDEO_DEMO_DOOMGENERIC_SEQ_TELEMETRY=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_MINIMAL=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME=1, -DVIDEO_DEMO_DOOMGENERIC_HW_PLANE_SCALE=1, -DVIDEO_DEMO_DOOMGENERIC_PRESENT_PAGEFLIP=1, -DA90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH="/tmp/a90-doomgeneric-v3108-input.sock", -DA90_DOOMGENERIC_BRIDGE_SHARED_FRAME_PATH="/tmp/a90-doomgeneric-v3108-shared-frame.bin", -DA90_DOOMGENERIC_BRIDGE_PACE_SOCKET_PATH="/tmp/a90-doomgeneric-v3108-pace.sock", -DA90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT=30570`
- Candidate type: `doomgeneric-hw-plane-scale-candidate`.
