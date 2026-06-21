# Native Init V3031 DOOMGENERIC Visible Frame Source Build

## Summary

- Cycle: `V3031`
- Track: active Video playback / DOOM capstone.
- Decision: `v3031-doomgeneric-visible-frame-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Device action: `none` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3031_doomgeneric_visible_frame.img`
- Boot SHA256: `1fefa60b9530cf4cfeb21f2419b77e7d9ca4258078899e3826a0c99918912fb4`
- Init: `A90 Linux init 0.10.75 (v3031-doomgeneric-visible-frame)`

## Included Delta

- Extends the private doomgeneric helper with `--wad-frame-dump <path> --frames N --output <frame>`.
- Adds native-init `video demo doom frame [frames] --wad runtime-private --sha256 EXPECTED`.
- The command verifies the SD WAD path/hash first, asks the helper for one bounded raw frame, then blits that frame through the existing KMS dumb-buffer path.
- The DEMO > DOOM menu item now launches an 8-frame WAD-backed visible-frame preview and restores the menu.
- Existing `verify`, `play`, and `engine-probe` command surfaces remain bounded.

## Runtime WAD Contract

- Runtime WAD root: `/mnt/sdext/a90/runtime/doom/v3028/`
- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Runtime WAD max bytes: `67108864`
- WAD files in ramdisk: `0`
- Public WAD files committed/present: `0`
- WAD bytes embedded in boot image: `0`

## Frame Contract

- Helper frame command: `/bin/a90_doomgeneric_private_engine_v3031 --wad-frame-dump /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 8 --output /tmp/a90-doomgeneric-v3031-frame.xbgr8888`
- Native command: `video demo doom frame 8 --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Frame path: `/tmp/a90-doomgeneric-v3031-frame.xbgr8888`
- Frame format: `xbgr8888-raw`
- Frame geometry: `640x400` stride `2560` bytes `1024000`
- KMS path: `existing-kms-dumb-buffer-blit-present`

## Private Engine Helper

- Bundled helper path: `/bin/a90_doomgeneric_private_engine_v3031`
- V3031 engine binary: `workspace/private/builds/native-init/v3031-doomgeneric-visible-frame/a90_doomgeneric_private_engine_v3031`
- V3031 engine SHA256: `45fca3ed017420c8368c99dcdd3b351053000b9bf26e653daa5d79bde704ce47`
- V3031 engine bytes: `1069960`
- Helper bundled in ramdisk: `1`

## Marker Check

- `A90 Linux init 0.10.75 (v3031-doomgeneric-visible-frame)`
- `v3031-doomgeneric-visible-frame`
- `doomgeneric-private-link-v3031-visible-frame`
- `/bin/a90_doomgeneric_private_engine_v3031`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `/tmp/a90-doomgeneric-v3031-frame.xbgr8888`
- `--wad-smoke`
- `--wad-frame-dump`
- `--output`
- `a90.doomgeneric.v3031.visible_frame=frame-dump-xbgr8888`
- `video demo doom frame [frames] --wad runtime-private --sha256`
- `video.demo.doom.frame=doomgeneric-sd-wad-visible-frame`
- `video.demo.doom.frame.display.presented=1`
- `menu.demo.doom.action=visible-frame-preview`
- `video.status.doomgeneric.visible_frame=1`
- `video.demo.asset.wad.embedded_in_boot=%d`
- `video.demo.input.otg_required=0`

## Safety

- No device action was performed by this builder.
- No flash, serial command, Wi-Fi action, sysfs write, evdev injection, uinput, PMIC, regulator, backlight, GPIO, GDSC, or forbidden partition path is touched.
- WAD/IWAD bytes remain only on the runtime SD path and are not copied into public, ramdisk, boot image, reports, or generated source.
- The frame dump is a bounded temporary raw-frame artifact path, not a WAD copy.
- The generated boot image and helper are private/untracked. Public output is limited to source, tests, and this metadata-only report.
- Rollback target remains `v2321-usb-clean-identity-rodata` for the next live unit.

## Host Validation

- `py_compile`: builder, selector, and focused tests.
- `unittest`: V3031 visible-frame tests, V3029 SD-WAD command tests, and selector tests.
- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3031 visible-frame command, frame path, SD WAD path/hash, and bounded helper markers.
- Ramdisk inventory: helper path present and WAD file count is zero.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3032`
- Type: rollback-gated live validation of V3031 visible-frame candidate.
- Scope: flash only the exact V3031 boot image through `native_init_flash.py`, health-check, run `video demo doom frame 8 --wad runtime-private --sha256 EXPECTED`, confirm KMS presentation markers, then rollback to V2321.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3031-doomgeneric-visible-frame", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3031-visible-frame", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3031", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_FRAME_PATH="/tmp/a90-doomgeneric-v3031-frame.xbgr8888", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300, -DA90_DOOMGENERIC_BRIDGE_FRAME_WIDTH=640, -DA90_DOOMGENERIC_BRIDGE_FRAME_HEIGHT=400, -DA90_DOOMGENERIC_BRIDGE_FRAME_STRIDE=2560, -DA90_DOOMGENERIC_BRIDGE_FRAME_BYTES=1024000`
- Candidate type: `doomgeneric-visible-frame-candidate`.
