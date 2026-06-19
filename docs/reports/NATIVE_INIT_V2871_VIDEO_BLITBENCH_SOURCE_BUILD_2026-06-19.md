# Native Init V2871 Video Blitbench Source Build

## Summary

- Cycle: `V2871`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2871-video-blitbench-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2871_video_blitbench.img`
- Boot SHA256: `2693a1bde100c9469615203a96f8e8aeaabc8bb4f701f7f0ea461b61420d925c`
- Init: `A90 Linux init 0.10.22 (v2871-video-blitbench)`
- Parent candidate: `v2859-audio-changelog-latest-refresh` plus the V2868 video command surface already in source.

## Included Delta

- Keeps the latest audio/core/productization baseline and the V2868 `video frame` / `video anim` KMS command surface.
- Extends `a90_kms_info` with `stride`, `map_size`, and `pixel_format` so host preprocessors can target the exact active framebuffer surface.
- Adds `a90_kms_begin_frame_no_clear()` for full-frame stream paths that overwrite every pixel without measuring an extra clear pass.
- Adds bounded, cancelable `video blitbench [frames<=240]` that copies a synthetic full-frame source row-by-row into the mapped KMS dumb buffer and presents each frame.
- Reports `video.blitbench.*` metrics: frames, bytes, elapsed ns, fps_milli, mbps_milli, geometry, stride, frame_bytes, and `pixel_format=xbgr8888`.
- Leaves frame-file streaming, arbitrary PCM-file playback, and A/V sync for later units after the live blit ceiling is measured.

## Video Metadata

- Version: `2`
- Source unit: `V2871`
- Commands: `video, video status, video frame, video demo, video anim, video blitbench`
- Benchmark bound: `frames<=240`
- Safety boundary: `no-venus-no-kgsl-no-raw-dsi-no-power-writes`

## Bundled Runtime Metadata

- Bundled audio artifact count: `15`
- Replay entry count: `11`
- Native manifest SHA256: `b29d72ad5b844a2749279d78259e79c731db4d5f12cd546bfd3c3bd122ed6864`
- Raw SET-cal bytes remain private; this report records only counts and hashes.

## Static Validation

- `py_compile`: V2871 builder.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.
- Marker check: generated boot image contains the V2871 `video.status.kms.*` and `video.blitbench.*` command markers.
- `video.status.kms.stride=`
- `video.status.kms.map_size=`
- `video.status.kms.pixel_format=xbgr8888`
- `video.status.next_blitbench=video blitbench [frames<=240]`
- `video.blitbench.presented=`
- `video.blitbench.fps_milli=`
- `video.blitbench.mbps_milli=`
- `videoblitbench`
- `file`: native-init and helper are AArch64 statically linked executables.
- `python3 -m unittest discover -s tests`: attempted; failed in pre-existing historical audio runner/API expectation tests unrelated to this V2871 KMS/video delta. The V2871 builder, compile, marker, and `git diff --check` validations passed.
- Next live unit should flash this exact image, run `video status`, `hide`, and bounded `video blitbench`, then rollback to `v2321`.

## Safety

- No device action was performed by this builder.
- This unit adds no Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.
- The benchmark uses synthetic frame data only; no copyrighted media, generated frame payloads, PCM payloads, boot images, or binaries are committed.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `video-blitbench-candidate`.
