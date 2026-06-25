# Native Init V3202 GPU G4 Solid Fill CCU Seqno Probe Source Build

## Summary

- Cycle: `V3202`
- Track: GPU G4 KGSL A6xx A2D solid-fill render plus CPU readback verification, with a Mesa-style post-blit CCU color timestamp event restored.
- Decision: `v3202-gpu-g4-solid-fill-ccu-seqno-probe-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3202_gpu_g4_solid_fill_ccu_seqno_probe.img`
- Boot SHA256: `2574f594da4e8e06c3ed4c3541ab112c71c2476aa7490b5d8634dd860c0ed763`
- Init: `A90 Linux init 0.11.29 (v3202-gpu-g4-solid-fill-ccu-seqno-probe)`

## Included Delta

- Keeps `gpu g4-solid-fill-probe` as the user-visible command and restores one post-blit `CP_EVENT_WRITE`: `PC_CCU_FLUSH_COLOR_TS` with timestamp bit, GPU address, and seqno payload.
- The child sequence is `open` -> `DRAWCTXT_CREATE` -> command/destination `GPUOBJ_ALLOC` -> `GPUOBJ_INFO` -> `mmap` -> prefill destination sentinel -> write Mesa/freedreno-derived A6xx A2D `CP_BLIT` command stream -> command `GPUOBJ_SYNC TO_GPU` -> `GPU_COMMAND` -> `TIMESTAMP_EVENT` fence -> bounded `WAITTIMESTAMP_CTXTID` -> read retired timestamp -> destination `GPUOBJ_SYNC FROM_GPU` -> verify solid-fill words -> cleanup.
- Keeps V3198's exclusion of `DEBUG_LABEL`, `CACHE_FLUSH_TS`, and `CACHE_INVALIDATE`; V3197 implicated the `CACHE_INVALIDATE` tail in the CP fault path, and V3201 showed the raw one-dword CCU event packet is unsafe.
- Keeps G0/G1/G2/G3 commands available as prerequisites and regression checks.
- The parent never enters KGSL `open()` or `ioctl()`; it only enforces timeout and reports metadata.

## Safety

- Boot partition only through `native_init_flash.py` in any future live step.
- Uses KGSL-direct normal command submission; no proprietary Adreno blob/EGL/Bionic path.
- No GDSC/regulator/PMIC/GPIO/power-rail write is included.
- No triangle, shader, compute grid, KMS blit, or display handoff is included in G4.
- The render target is a private KGSL GPU object, and readback is limited to the first 16 32-bit words after KGSL `GPUOBJ_SYNC FROM_GPU`.
- `RB_DBG_ECO_CNTL` blit-mode toggling is deliberately skipped because Mesa sources route its value through GPU-specific `fd_dev_info.magic`; this unit does not invent that magic value.
- V3198 removed all post-blit events and avoided the V3196 dmesg fault but left readback at the sentinel pattern. V3202 restores only the Mesa-derived CCU color clean event, encoded as a timestamp event with a dedicated KGSL object target.

## Source Basis

- Local Samsung KGSL UAPI/driver source: `IOCTL_KGSL_GPU_COMMAND` returns a timestamp, `IOCTL_KGSL_TIMESTAMP_EVENT` can create a fence fd for that timestamp, and `IOCTL_KGSL_GPUOBJ_SYNC` performs cache sync by GPU object id.
- Mesa/freedreno PM4 source: type4/type7 odd-parity packet helpers, A6xx `fd6_clear_buffer()` A2D clear path, `CP_SET_MARKER(RM6_BLIT2DSCALE)`, `CP_BLIT(BLIT_OP_SCALE)`, and A6xx register XML enum values.
- Local live evidence: `docs/reports/NATIVE_INIT_V3197_GPU_G4_SOLID_FILL_PROBE_LIVE_INCIDENT_2026-06-25.md` identified the V3196 post-blit event-write tail as unsafe; `docs/reports/NATIVE_INIT_V3199_GPU_G4_SOLID_FILL_NOEVENT_LIVE_2026-06-25.md` showed that removing all post-blit events avoids faults but leaves the target buffer unchanged; `docs/reports/NATIVE_INIT_V3201_GPU_G4_CCU_FLUSH_LIVE_INCIDENT_2026-06-25.md` showed that a one-dword raw CCU event packet is unsafe.
- Mesa references: `https://docs.mesa3d.org/drivers/freedreno.html`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_blitter.cc`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.h`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_barrier.cc`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_pm4.h`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_gpu_event.h`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_common.xml`.

## Validation

- `py_compile`: V3202 builder and focused tests.
- `unittest`: V3202 GPU G4 source contract plus V3198/V3196/V3194/V3192/V3190 regression contracts.
- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3202 identity, G0/G1/G2/G3 markers, and G4 solid-fill markers.
- `git diff --check`: PASS.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3202-gpu-g4-solid-fill-ccu-seqno-probe", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3202-gpu-g4-solid-fill-ccu-seqno-probe", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3202", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3202-raw-fallback-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_INPUT_STATE_PATH="/tmp/a90-doomgeneric-v3202-input.state", -DA90_DOOMGENERIC_BRIDGE_INPUT="udp-ncm-to-DG_GetKey-with-serial-doompad-fallback", -DA90_DOOMGENERIC_BRIDGE_SOUND="native-doom-sfx-gpu-g4-solid-fill-ccu-seqno-probe-v3202", -DA90_DOOMGENERIC_AUDIO_CORUN_MODE="native-doom-sfx-gpu-g4-solid-fill-ccu-seqno-probe-v3202", -DA90_DOOMGENERIC_AUDIO_PCM_STREAM_PATH="/cache/a90-runtime/a90-doomgeneric-v3202-sfx.pcmstream", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=960, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=600, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=3840, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=2304000, -DA90_DOOMGENERIC_BRIDGE_LOOP_FRAME_MS=28, -DVIDEO_DEMO_DOOMGENERIC_PRESENTER_POLL_MS=4, -DA90_DOOMGENERIC_AUDIO_CORUN=1, -DA90_DOOMGENERIC_AUDIO_CORUN_STREAM=1, -DA90_DOOMGENERIC_AUDIO_CORUN_DURATION_MS=240000, -DA90_DOOMGENERIC_AUDIO_CORUN_REFRESH_MS=0, -DA90_DOOMGENERIC_AUDIO_CORUN_AMPLITUDE_MILLI=150, -DA90_DOOMGENERIC_PHYSICAL_BUTTON_EXIT=1, -DVIDEO_DEMO_DOOMGENERIC_REUSE_FRAME_BUFFER=1, -DVIDEO_DEMO_DOOMGENERIC_DIRECT_SHARED_BLIT=1, -DVIDEO_DEMO_DOOMGENERIC_FOREGROUND_FRAME_LOG=0, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_METRICS_INTERVAL_FRAMES=1800, -DVIDEO_DEMO_DOOMGENERIC_DASHBOARD_STATUS_INTERVAL_FRAMES=300, -DVIDEO_DEMO_DOOMGENERIC_FRAME_TIMING_PROBE=1, -DVIDEO_DEMO_DOOMGENERIC_SEQ_TELEMETRY=1, -DA90_DOOMGENERIC_NATIVE_DASHBOARD=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD_FAST=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD_READABLE=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD_SECTIONED=1, -DA90_DOOMGENERIC_NATIVE_DEMO_HUD_LARGE_GROUPS=1, -DVIDEO_DEMO_DOOMGENERIC_NO_FULL_CLEAR=1, -DVIDEO_DEMO_DOOMGENERIC_PRESENT_PAGEFLIP=1, -DA90_DOOMGENERIC_BRIDGE_INPUT_SOCKET_PATH="/tmp/a90-doomgeneric-v3202-input.sock", -DA90_DOOMGENERIC_BRIDGE_SHARED_FRAME_PATH="/tmp/a90-doomgeneric-v3202-shared-frame.bin", -DA90_DOOMGENERIC_BRIDGE_PACE_SOCKET_PATH="/tmp/a90-doomgeneric-v3202-pace.sock", -DA90_DOOMGENERIC_BRIDGE_TICK_TELEMETRY_PATH="/tmp/a90-doomgeneric-v3202-tick-telemetry.txt", -DVIDEO_DEMO_DOOMGENERIC_TICK_TELEMETRY_SUMMARY=1, -DA90_DOOMGENERIC_BRIDGE_INPUT_UDP_PORT=30570`
- Candidate type: `gpu-g4-solid-fill-ccu-seqno-probe-candidate`.
