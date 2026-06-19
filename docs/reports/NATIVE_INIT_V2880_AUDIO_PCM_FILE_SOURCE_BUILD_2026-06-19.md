# Native Init V2880 Audio PCM-File Source Build

## Summary

- Cycle: `V2880`
- Track: active Video playback pipeline; this unit adds the missing PCM-file audio source needed for A/V bundles.
- Decision: `v2880-audio-pcm-file-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2880_audio_pcm_file.img`
- Boot SHA256: `674c7ff223f295be0e53e3fd4636b2dd4f54a6c9615a7b6fa8833951fdf3dc44`
- Init: `A90 Linux init 0.10.26 (v2880-audio-pcm-file)`
- Parent validated state: V2879 live-proved raw-stride frame streaming with DRM page-flip events.

## Included Delta

- Adds optional `audio play ... --pcm-file PATH` while keeping the default generated-tone/chime path unchanged.
- Restricts PCM-file sources to `/cache/a90-runtime`, rejects `..`, and opens the file with `O_NOFOLLOW`.
- Before any ALSA write, checks that the file is regular, large enough for the requested duration, seekable, and peak amplitude is within the profile cap.
- Streams bounded S16LE stereo chunks from the validated file through the existing integrated ADSP/snd/app-type/SET-cal/route/PCM path.
- Keeps the V2878/V2879 KMS page-flip video stream command surface intact for the next A/V sync unit.

## Audio PCM-File Contract

- Command shape: `audio play internal-speaker-safe --mode listen --duration-ms N --amplitude-milli M --pcm-file /cache/a90-runtime/pkg/.../audio.s16le --execute`.
- File format: raw interleaved S16LE matching the active speaker profile: 48 kHz, stereo, 16-bit.
- Duration remains bounded by the existing profile duration cap; amplitude remains bounded by a pre-write peak scan.
- Raw PCM files are private runtime artifacts and are not committed.

## Retained Video Metadata

- Version: `6`
- Commands: `video, video status, video frame, video demo, video anim, video blitbench, video flipprobe, video stream`
- Safety boundary: `no-venus-no-kgsl-no-raw-dsi-no-power-writes`
- Page-flip stream path marker retained: `kms-dumb-buffer-pageflip`.

## Bundled Runtime Metadata

- Bundled audio artifact count: `15`
- Replay entry count: `11`
- Native manifest SHA256: `b29d72ad5b844a2749279d78259e79c731db4d5f12cd546bfd3c3bd122ed6864`
- Raw SET-cal bytes remain private; this report records only counts and hashes.

## Static Validation

- `py_compile`: V2880 builder.
- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V2880 PCM-file and retained page-flip markers.
- `audio.play.pcm_file_supported=1`
- `audio.play.pcm_file.path_allowed=`
- `audio.play.pcm_file.validated=1`
- `audio.play.pcm_file.amplitude_within_cap=`
- `audio.play.execute.source=`
- `audio.play.execute.plan.source=`
- `audio.play.execute.plan.pcm_file=`
- `--pcm-file PATH`
- `kms-dumb-buffer-pageflip`
- `file`: native-init and helper are AArch64 statically linked executables.
- Device validation is deferred to the next V-iteration: flash this exact image, install a bounded private PCM fixture, run dry-run/execute, then rollback to `v2321`.

## Safety

- No device action was performed by this builder.
- This unit adds no Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.
- PCM-file execution remains bounded by existing audio caps and pre-write amplitude scanning.
- Rollback target remains `v2321-usb-clean-identity-rodata`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1, -DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1, -DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1, -DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1, -DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1, -DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1, -DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1, -DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1, -DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1, -DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1, -DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1, -DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1, -DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1, -DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1, -DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1, -DNETSERVICE_USB_HELPER="/bin/a90_usbnet", -DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl", -DNETSERVICE_TOYBOX="/bin/toybox", -DA90_BUSYBOX_HELPER="/bin/busybox", -DA90_WIFI_LIFECYCLE_MODEM_OWNER=1, -DA90_TRANSPORT_STATUS_CONTRACT=1, -UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH, -DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0, -DAUDIO_SETCAL_BUNDLED_PREFIX="/a90/audio", -DAUDIO_SETCAL_DEFAULT_MANIFEST_PATH="/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", -DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1`
- Candidate type: `audio-pcm-file-candidate`.
