# Native Init V2878 Video Stream Page-Flip Source Build

## Summary

- Cycle: `V2878`
- Track: active Video playback pipeline on the existing KMS display.
- Decision: `v2878-video-stream-pageflip-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2878_video_stream_pageflip.img`
- Boot SHA256: `5f33038c1812dabd6f46fa724dddee39b8ddaf346b96f53155ab42c84cd29587`
- Init: `A90 Linux init 0.10.25 (v2878-video-stream-pageflip)`
- Parent candidate: V2877 proved page-flip events on the existing KMS dumb-buffer display path.

## Included Delta

- Keeps the V2874 raw-stride `video stream` reader and V2876/V2877 page-flip helper/probe.
- Adds optional `--present setcrtc|pageflip` parsing to `video stream`; the default remains `setcrtc` for compatibility with the already-proven V2875 path.
- In `pageflip` mode, primes the CRTC with the existing SETCRTC present once, then uses `a90_kms_present_pageflip()` for each streamed frame.
- Reports `video.stream.present_mode`, `video.stream.flip_events`, last flip sequence/CRTC/timestamp, and uses `path=kms-dumb-buffer-pageflip` only when the opt-in mode is active.
- Leaves A/V sync and PCM-file playback for later units after the page-flip stream mode is live-proven.

## Video Metadata

- Version: `5`
- Source unit: `V2878`
- Commands: `video, video status, video frame, video demo, video anim, video blitbench, video flipprobe, video stream`
- Stream present modes: `setcrtc, pageflip`
- Safety boundary: `no-venus-no-kgsl-no-raw-dsi-no-power-writes`

## Bundled Runtime Metadata

- Bundled audio artifact count: `15`
- Replay entry count: `11`
- Native manifest SHA256: `b29d72ad5b844a2749279d78259e79c731db4d5f12cd546bfd3c3bd122ed6864`
- Raw SET-cal bytes remain private; this report records only counts and hashes.

## Static Validation

- `py_compile`: V2878 builder.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V2878 stream page-flip option/report markers.
- `video.status.next_stream_pageflip=video stream --manifest PATH --video-only [--frames N] --present pageflip`
- `video.stream.requested_present=`
- `video.stream.present_mode=`
- `video.stream.flip_events=`
- `video.stream.path=%s`
- `kms-dumb-buffer-pageflip`
- `--present setcrtc|pageflip`
- `videostreamprime`
- `file`: native-init and helper are AArch64 statically linked executables.
- Next live unit should flash this exact image, install a private A90VSTR1 fixture, run `video stream ... --present pageflip`, then rollback to `v2321`.

## Safety

- No device action was performed by this builder.
- This unit adds no Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.
- Page-flip mode remains opt-in and uses the same existing KMS card0 dumb buffers as V2877.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `video-stream-pageflip-candidate`.
