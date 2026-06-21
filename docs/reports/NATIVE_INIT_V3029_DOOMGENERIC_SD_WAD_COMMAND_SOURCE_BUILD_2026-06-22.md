# Native Init V3029 DOOMGENERIC SD WAD Command Source Build

## Summary

- Cycle: `V3029`
- Track: active Video playback / DOOM capstone.
- Decision: `v3029-doomgeneric-sd-wad-command-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Device action: `none` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3029_doomgeneric_sd_wad_command.img`
- Boot SHA256: `9b45abb847ac64c9032f0e873038a3abf577e27f2dabc2ceccad8cd8e95cf804`
- Init: `A90 Linux init 0.10.74 (v3029-doomgeneric-sd-wad-command)`

## Included Delta

- Extends `a90_doomgeneric_bridge` with native `stat` + magic + SHA256 WAD verification.
- Adds bounded SD-WAD command handling for `video demo doom verify --wad runtime-private --sha256 EXPECTED`.
- Adds bounded SD-WAD smoke command handling for `video demo doom play [frames] --wad runtime-private --sha256 EXPECTED`.
- Builds and bundles a V3029 private doomgeneric helper that accepts `--wad-smoke <path> --frames N` and runs the engine against the SD WAD.
- Keeps serial control as the primary input path: `serial-doompad-to-DG_GetKey`.
- Keeps sound disabled: `-nosound -nomusic`.

## Runtime WAD Contract

- Runtime WAD root: `/mnt/sdext/a90/runtime/doom/v3028/`
- Runtime WAD path: `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- Expected WAD SHA256: `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- Runtime WAD max bytes: `67108864`
- WAD files in ramdisk: `0`
- Public WAD files committed/present: `0`
- WAD bytes embedded in boot image: `0`

## Private Engine Helper

- Bundled helper path: `/bin/a90_doomgeneric_private_engine_v3029`
- V3029 engine binary: `workspace/private/builds/native-init/v3029-doomgeneric-sd-wad-command/a90_doomgeneric_private_engine_v3029`
- V3029 engine SHA256: `435dc0bda50dff6c27410ed727d4d513c02bfba89e876ff654a045cf00d26b44`
- V3029 engine bytes: `1069912`
- Helper bundled in ramdisk: `1`
- Helper command: `/bin/a90_doomgeneric_private_engine_v3029 --wad-smoke /mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD --frames 16`

## Command Surface

- `video demo doom verify --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `video demo doom play [frames] --wad runtime-private --sha256 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `video demo doom status` remains status-only and reports SD-WAD path/hash/readiness markers.
- `video demo doom engine-probe` remains a bounded no-WAD helper probe.
- Menu status remains status-only; it does not launch WAD-backed gameplay.

## Marker Check

- `A90 Linux init 0.10.74 (v3029-doomgeneric-sd-wad-command)`
- `v3029-doomgeneric-sd-wad-command`
- `doomgeneric-private-link-v3029-sd-wad-smoke`
- `/bin/a90_doomgeneric_private_engine_v3029`
- `/mnt/sdext/a90/runtime/doom/v3028/`
- `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`
- `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`
- `--wad-smoke`
- `a90.doomgeneric.v3029.wad_smoke=bounded`
- `video demo doom verify --wad runtime-private --sha256`
- `video demo doom play [frames] --wad runtime-private --sha256`
- `video.demo.doom.verify=doomgeneric-sd-wad`
- `video.demo.doom.play=doomgeneric-sd-wad-smoke`
- `video.demo.doom.play.verify.sha256_match=%d`
- `video.demo.asset.wad.embedded_in_boot=%d`
- `video.demo.input.otg_required=0`

## Safety

- No device action was performed by this builder.
- No flash, serial command, Wi-Fi action, sysfs write, evdev injection, uinput, PMIC, regulator, backlight, GPIO, GDSC, or forbidden partition path is touched.
- WAD/IWAD bytes are not copied into public, ramdisk, boot image, reports, or generated source.
- The generated boot image and helper are private/untracked. Public output is limited to source, tests, and this metadata-only report.
- Rollback target remains `v2321-usb-clean-identity-rodata` for the next live unit.

## Host Validation

- `py_compile`: builder, selector, and focused tests.
- `unittest`: V3029 SD-WAD command tests and selector tests.
- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3029 command, SD WAD path/hash, and bounded helper markers.
- Ramdisk inventory: helper path present and WAD file count is zero.
- `git diff --check`: PASS.

## Next Unit

- Run ID: `V3030`
- Type: rollback-gated live validation of V3029 SD-WAD command candidate.
- Scope: flash only the exact V3029 boot image through `native_init_flash.py`, health-check, run `video demo doom verify --wad runtime-private --sha256 EXPECTED` and a short bounded `video demo doom play ...`, then rollback to V2321.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1, -DA90_DOOMGENERIC_BRIDGE_CANDIDATE="v3029-doomgeneric-sd-wad-command", -DA90_DOOMGENERIC_BRIDGE_ENGINE="doomgeneric-private-link-v3029-sd-wad-smoke", -DA90_DOOMGENERIC_BRIDGE_HELPER_PATH="/bin/a90_doomgeneric_private_engine_v3029", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT="/mnt/sdext/a90/runtime/doom/v3028/", -DA90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_PATH="/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD", -DA90_DOOMGENERIC_BRIDGE_EXPECTED_WAD_SHA256="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771", -DA90_DOOMGENERIC_BRIDGE_MAX_WAD_BYTES=67108864, -DA90_DOOMGENERIC_BRIDGE_MAX_PLAY_FRAMES=300`
- Candidate type: `doomgeneric-sd-wad-command-candidate`.
