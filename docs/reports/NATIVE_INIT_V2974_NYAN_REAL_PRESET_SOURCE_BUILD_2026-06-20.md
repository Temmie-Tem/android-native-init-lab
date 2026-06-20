# Native Init V2974 Nyan Real Preset Source Build

## Summary

- Cycle: `V2974`
- Track: active Video playback pipeline / Nyan Cat compact color demo.
- Decision: `v2974-nyan-real-preset-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2974_nyan_real_preset.img`
- Boot SHA256: `e6ac9bc08829c465e2126654b1f7020eab5e5cfb8491e7fc9d9a297e3b514410`
- Init: `A90 Linux init 0.10.59 (v2974-nyan-real-preset)`

## Included Delta

- Bumps `video.status.version` to `9` for the expanded Nyan command/menu surface.
- Adds the content-addressed `video cache preset nyan` mapping to the V2973 private `A90VSTR2 pal8-rle` preview stream.
- Adds `video demo nyan` by reusing the existing SHA-addressed cache preset wrapper and Player HUD layout.
- Adds `DEMO > NYAN CAT` as a bounded 300-frame / 10 s A/V preview entry with low-amplitude PCM playback.
- Keeps Bad Apple presets and the existing `A90VSTR2 pal8-rle` decoder path intact.
- Does not add GPU, Venus, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths.

## Asset Contract

- Nyan asset ID: `nyancat-v2973-pal8-rle-preview`
- Nyan stream SHA256: `9a8d91956218acf674b7d99d421467effec442fdde1dbbea8635b8f47085c573`
- Nyan audio SHA256: `4c3774553195c04166a3a83de793253696a5bee60afe83a04219419fc28e43de`
- Nyan audio runtime path: `/cache/a90-runtime/pkg/av/v2973/audio/nyancat.s16le`
- Media bytes remain private/untracked; this image carries only the player and SHA/path contract.

## Marker Check

- `A90 Linux init 0.10.59 (v2974-nyan-real-preset)`
- `video.status.version=9`
- `video.status.nyan_pal8_rle=1`
- `video cache preset [badapple|badapple-scale|nyan]`
- `video demo [badapple|badapple-scale|nyan]`
- `nyancat-v2973-pal8-rle-preview`
- `9a8d91956218acf674b7d99d421467effec442fdde1dbbea8635b8f47085c573`
- `DEMO / NYAN CAT`
- `NYAN CAT`
- `menu.demo.nyan.action=play-av-preview`
- `menu.demo.nyan.frames=300`
- `menu.demo.nyan.audio_duration_ms=10000`
- `menu.demo.nyan.audio_pcm=/cache/a90-runtime/pkg/av/v2973/audio/nyancat.s16le`
- `menu.demo.nyan.audio_pcm_gain_milli=780`
- `menu.demo.nyan.video_present=setcrtc`
- `pal8-rle`
- `A90VSTR2`

## Static Validation

- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V2974 identity, Nyan preset SHA/asset ID, menu action markers, `A90VSTR2`, and `pal8-rle` strings.
- Device validation is deferred to V2975: flash this exact image, seed the V2973 private stream+PCM to SD/runtime cache, run `video demo nyan status|verify|play`, then health-check/rollback.

## Bundled Runtime Metadata

- Bundled audio artifact count: `15`
- Replay entry count: `11`
- Native manifest SHA256: `b29d72ad5b844a2749279d78259e79c731db4d5f12cd546bfd3c3bd122ed6864`

## Safety

- No device action was performed by this builder.
- Generated streams, PCM, boot images, and private caches remain private/untracked.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `nyan-real-preset-candidate`.
