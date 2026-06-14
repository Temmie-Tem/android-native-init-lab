# Native Init V2331 Audio ADSP Firmware Class Native Path Source Build

## Summary

- Cycle: `V2331`
- Track: audio AUD-2 gated firmware preflight correction, source/build-only.
- Decision: `v2331-audio-adsp-fwclass-native-path-source-build-pass`
- Result: PASS
- Device flash: `no`.
- Device action: `none`.
- Manifest: `workspace/private/builds/native-init/v2331-audio-adsp-fwclass-native-path/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2331_audio_adsp_fwclass_native_path.img`
- Boot SHA256: `8d3e95f7a638fff508d893ee321c0569a04debbad2d16ed7c34188c0a9d9de74`
- Init: `A90 Linux init 0.9.291 (v2331-audio-adsp-fwclass-native-path)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Change

- Keeps the native-init command surface at `audio [adsp-status|status|adsp-boot-once]`.
- Retains the V2329 sparse ADSP firmware segment model: `adsp.b00`..`adsp.b11` plus `adsp.b13`..`adsp.b16`; `adsp.b12` is not expected.
- Retains the V2329 effective `firmware_class.path` preflight gate before any ADSP boot write.
- Disables the legacy Wi-Fi-only `A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH` override for this audio artifact so PID1 should not rewrite `firmware_class.path` to `/mnt/vendor/firmware`.
- Expected effective loader path is the boot cmdline path `/vendor/firmware_mnt/image`, which V2330 proved contains the complete sparse ADSP set.
- If all preflight checks pass in a future gated live run, the only activation write remains `1\n` to `/sys/kernel/boot_adsp/boot` once.
- No `tinymix`, `tinyplay`, PCM, HAL, adsprpc invoke/ioctl, `/dev/subsys_adsp` open, retry, unload, or playback path is added.

## Host Evidence Correction

- V2328 correctly blocked before activation, but the immediate `adsp.b12` discriminator was a false-negative in the V2327 preflight model.
- The private AUD-0 NON-HLOS FAT directory inventory lists `ADSP.B00`..`ADSP.B11` and `ADSP.B13`..`ADSP.B16`, plus `ADSP.MDT`; it does not list `ADSP.B12`.
- Therefore a complete stock ADSP image for this build is the sparse 16-segment set, not a contiguous 17-segment set.
- V2328 also showed `firmware_class.path=/mnt/vendor/firmware` while V2327 validated only `/vendor/firmware_mnt/image`; V2331 treats the effective firmware_class path as the write gate.
- V2330 proved `/vendor/firmware_mnt/image` has the corrected sparse ADSP set while the legacy effective path `/mnt/vendor/firmware` has none.

## Firmware Class Path Strategy

- Mode: `disable-legacy-wifi-fwclass-vendor-path`.
- Runtime sysfs write added by this build: `no`.
- The inherited Wi-Fi firmware mounts stay enabled; only the legacy `/mnt/vendor/firmware` firmware_class override is disabled.
- The live discriminator is direct: `audio adsp-status` must report `audio.firmware_class_path=/vendor/firmware_mnt/image` and `audio.firmware_class.adsp_complete=yes` before `audio adsp-boot-once` is allowed to write.

## Safety Boundary

- This is not AUD-2 live execution. It only fixes the gated command preflight that AUD-2 would use after explicit operator approval.
- No ADSP activation write was run. No flash was performed by this source-build unit.
- The command remains intentionally not safe-retryable at the `a90ctl` layer because it can write once after token + preflight.
- Future live use still requires the explicit AUD-2 operator phrase from V2325 and the AGENTS.md flash/rollback gates.

## USB Baseline Retained

- Parent descriptor remains V2321: `A90-LNX` / `A90 Linux ARM64` / `A90NATIVE001`.
- V2323 named multi-LUN behavior is retained:
- `lun.0` model `A90-INTERNAL`, FAT label `A90INTERNAL`, backing `/cache/a90-usb-mass-storage-v2323-internal.img`.
- `lun.1` model `A90-SD`, FAT label `A90SD`, backing `/cache/a90-usb-mass-storage-v2323-sd.img`.

## Helper Flags

- `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_SINK=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_MCFG_READBACK=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_TMPFS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_LOGDW_ORDER_TIMESTAMPS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_READY_BEFORE_WLFW_VOTE=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_READWRITE_TRANSITION_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_PERMGR_VOTE_FOCUSED_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_WLFW_LATE_MSG21_FOCUSED_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_QCACLD_POST_BDF_FOCUSED_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_TMPFS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_AUTODIR_PARITY=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PROCESS_NAMESPACE_AUDIT=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1`
- `-DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1`
- `-DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1`
- `-DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1`
- `-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1`
- `-DA90_WIFI_TEST_BOOT_ICNSS_REGISTER_PROBE_STACK_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_FIRMWARE_CLASS_FALLBACK_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1`
- `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`

## Init Extra Flag Override

- `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=1`
- `-DNETSERVICE_USB_HELPER="/bin/a90_usbnet"`
- `-DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl"`
- `-DNETSERVICE_TOYBOX="/bin/toybox"`
- `-DA90_BUSYBOX_HELPER="/bin/busybox"`
- `-DA90_WIFI_LIFECYCLE_MODEM_OWNER=1`
- `-DA90_TRANSPORT_STATUS_CONTRACT=1`
- `-UA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH`
- `-DA90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH=0`

## Static Validation

- Source build: PASS.
- `file` on init binary: recorded by builder output.
- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2331_audio_adsp_fwclass_native_path.py`: PASS.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS (`996` tests).
- `git diff --check`: PASS.
