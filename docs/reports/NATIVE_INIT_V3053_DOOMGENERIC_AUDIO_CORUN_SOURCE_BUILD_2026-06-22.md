# Native Init V3053 DOOMGENERIC Audio Co-run Source Build

## Summary

- Cycle: `V3053`
- Track: active Video playback / DOOM capstone.
- Decision: `v3053-doomgeneric-audio-corun-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3053_doomgeneric_audio_corun.img`
- Boot SHA256: `dc863e16cd30852894a9232b1f8630a619e673bf49fb819b82a2743542733b71`
- Init: `A90 Linux init 0.10.85 (v3053-doomgeneric-audio-corun)`

## Included Delta

- Keeps V3051 DOOM autostart/probe behavior and V3047 batch input.
- Enables `A90_DOOMGENERIC_AUDIO_CORUN=1` so `video demo doom loop-start` starts the existing native audio worker with a bounded internal-speaker tone.
- Adds loop-start/loop-stop markers for the audio co-run path and records that this is not real DOOM SFX.
- Updates `audio stop --execute` to terminate the tracked async audio worker before resetting playback route.
- Leaves the private DOOM engine argv unchanged: `-nosound -nomusic` remains active.

## Audio Co-run Contract

- Sound mode marker: `native-audio-corun-tone-v3053`
- Co-run enabled: `1`
- Co-run mode: `native-audio-corun-tone-v3053`
- Duration: `10000` ms
- Amplitude: `80` milli
- Source: `native-bounded-tone` through `audio play internal-speaker-safe --mode listen --execute`.
- Real DOOM SFX backend: `0` for this unit.

## Runtime Contract

- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Frame path: `/tmp/a90-doomgeneric-v3053-audio-corun-frame.xbgr8888`
- Input state path: `/tmp/a90-doomgeneric-v3053-input.state`
- Autostart marker: `a90.doomgeneric.v3049.autostart=warp-e1m1-skill2`
- Probe marker: `a90.doomgeneric.v3051.probe=autostart-argv12`
- Audio marker: `a90.doomgeneric.v3053.audio=native-audio-corun-tone-real-sfx-disabled`

## Marker Check

- `A90 Linux init 0.10.85 (v3053-doomgeneric-audio-corun)`
- `v3053-doomgeneric-audio-corun`
- `doomgeneric-private-link-v3053-audio-corun`
- `/bin/a90_doomgeneric_private_engine_v3053`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3053-audio-corun-frame.xbgr8888`
- `/tmp/a90-doomgeneric-v3053-input.state`
- `a90.doomgeneric.v3053.audio=native-audio-corun-tone-real-sfx-disabled`
- `native-audio-corun-tone-v3053`
- `video.demo.doom.audio_corun.enabled=`
- `video.demo.doom.audio_corun.mode=`
- `video.demo.doom.audio.corun=1`
- `video.demo.doom.audio.source=native-bounded-tone`
- `video.demo.doom.audio.real_doom_sfx=0`
- `video.demo.doom.audio.start.rc=`
- `video.demo.doom.loop_start.audio_nonfatal=1`
- `video.demo.doom.audio.stop.requested=1`
- `audio.stop.worker.tracked_pid=`
- `audio.stop.worker.stop_rc=`
- `doompad.batch=state-mask-v3047`
- `video.demo.doom.clear.reason=`
- `video.demo.doom.loop_start.continuous`
- `video.demo.doom.dashboard.native=1`
- `host_doompad_dashboard_v3035.py`
- `host_doompad_keyboard_v3033.py`
- `video.demo.input.otg_required=0`

## Validation

- `py_compile`: builder and focused tests.
- `unittest`: V3053 source contract plus V3051/V3049 regressions.
- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3053 audio co-run, V3051 probe, V3049 autostart/clear, batch-input, and continuous-loop markers.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3054`
- Type: rollback-gated live validation of V3053 audio co-run candidate.
- Scope: flash exact V3053 boot image, health-check, run `video demo doom status`, `loop-start`, verify audio worker/status markers, verify `loop-stop` stops the tracked worker and clears the screen.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3053-doomgeneric-audio-corun", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3053-audio-corun", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3053", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3053-audio-corun-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3053-input.state", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-audio-corun-tone-v3053", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=33, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=10000, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=80, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME=1`
- Candidate type: `doomgeneric-audio-corun-candidate`.
