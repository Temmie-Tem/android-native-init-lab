# A90 H38 Bad Apple Boot-Chime Serialization H0

- Cycle: `H38`
- Decision: `h38-badapple-boot-chime-serialized-host-build`
- Init: `A90 Linux init 0.12.002 (h38-badapple-boot-chime-serialized-v1)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_h38_badapple_boot_chime_serialized_v2.img`
- Boot SHA256: `d96468eb429d7d64c94787cab4bd423136e60a480e73d19c8046e33b6b2606e9`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img`
- Device action: `none`
- Runtime result: `unproved`

## Change

- Runs boot-chime setup from PID1 so its asynchronous PCM worker remains tracked by PID1.
- Removes the late untracked wrapper-spawn race with the physical Bad Apple menu action.
- Keeps the existing bounded chime, menu pre-stop, audio safety caps, and boot-only rollback model.

## Boundary

- This host build does not prove cold-boot playback, menu launch, audio, video, or rollback.
- Any live use requires a fresh reviewed A90 F1 run after exact V2321 health is restored.

## Candidate hazard binding

- Hazard ID: `A90_H38_V3402_IDENTITY_ONLY_BOOT_CHIME_SERIALIZATION_TEMPORARY_EVIDENCE_CANDIDATE`
- Statement: `H38 preserves the exact V3402 non-init boot components and private Bad Apple engine but replaces PID1 with a source-built boot-chime ownership repair; cold-boot readiness, physical menu launch, synchronized audio/video playback, and rollback health remain unproved until one attended boot-only F1 run with exact V2321 recovery.`
- Statement SHA256: `3dcb6ab936636f30fd8804feea97f43daec94a375cdaaaaa6fe8a38838ceac3c`
- Acceptance at H0 means only that the temporary-candidate risk is explicit; it does not prove runtime behavior or grant live authority.

## Metadata

- Helper flags: ``
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="h38-badapple-boot-chime-serialized-v1", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3402-dpublic-hud-presenter-restart-policy", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3402", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3402-raw-fallback-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3402-input.state", -DA90_DOOMGENERIC_BRIDGE_INPUT="udp-ncm-to-DG_GetKey-with-serial-doompad-fallback", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-doom-sfx-softap-s4-transfer-server-v3402", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-doom-sfx-softap-s4-transfer-server-v3402", -DA90_DOOMGENERIC_AUDIO_PCM_STREAM_PATH="/cache/a90-runtime/a90-doomgeneric-v3402-sfx.pcmstream", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=960, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=600, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=3840, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=2304000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=28, -DVIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS=4, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_STREAM=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=240000, -DA90_DOOMGENERIC_AUDIO_CORUN_REFRESH_MS=0, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=150, -DA90_DOOMGENERIC_PHYSICAL_BUTTON_EXIT=1, -DVIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER=1, -DVIDEO_DEMO_DOOMGENERIC_DIRECT_SHARED_BLIT=1, -DVIDEO_DEMO_DOOMGENERIC_FOREGROUND_FRAME_LOG=0, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES=1800, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_STATUS_INTERVAL_FRAMES=300, -DVIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE=1, -DVIDEO_DEMO_DOOMGENERIC_SEQ_TELEMETRY=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD_FAST=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD_READABLE=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD_SECTIONED=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD_LARGE_GROUPS=1, -DVIDEO_DEMO_DOOMGENERIC_NO_FULL_CLEAR=1, -DVIDEO_DEMO_DOOMGENERIC_PRESENT_PAGEFLIP=1, -DA90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH="/tmp/a90-doomgeneric-v3402-input.sock", -DA90_DOOMGENERIC_BRIDGE_SHARED_FRAME_PATH="/tmp/a90-doomgeneric-v3402-shared-frame.bin", -DA90_DOOMGENERIC_BRIDGE_PACE_SOCKET_PATH="/tmp/a90-doomgeneric-v3402-pace.sock", -DA90_DOOMGENERIC_BRIDGE_TICK_TELEMETRY_PATH="/tmp/a90-doomgeneric-v3402-tick-telemetry.txt", -DVIDEO_DEMO_DOOMGENERIC_TICK_TELEMETRY_SUMMARY=1, -DA90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT=30570`
- Candidate type: `temporary-badapple-evidence-boot-chime-serialization`.
