# Native Init V2329 Audio ADSP Firmware Preflight Source Build

## Summary

- Cycle: `V2329`
- Track: audio AUD-2 gated firmware preflight correction, source/build-only.
- Decision: `v2329-audio-adsp-fw-preflight-source-build-pass`
- Result: PASS
- Device flash: `no`.
- Device action: `none`.
- Manifest: `workspace/private/builds/native-init/v2329-audio-adsp-fw-preflight/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2329_audio_adsp_fw_preflight.img`
- Boot SHA256: `8ab5ae3bbd750ee871c52b040905652683894f9816e7c4e29bfae2b2695638d8`
- Init: `A90 Linux init 0.9.290 (v2329-audio-adsp-fw-preflight)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Change

- Keeps the native-init command surface at `audio [adsp-status|status|adsp-boot-once]`.
- Corrects the ADSP firmware segment model from contiguous `adsp.b00`..`adsp.b16` to the stock sparse NON-HLOS set `adsp.b00`..`adsp.b11` plus `adsp.b13`..`adsp.b16`; `adsp.b12` is not expected.
- `audio adsp-status` now reports both the mounted APNHLOS firmware directory and the effective `firmware_class.path` directory with ADSP segment model, count, missing-list, and completion status.
- `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` still refuses without the exact token, but now also refuses if the effective `firmware_class.path` does not itself expose a complete ADSP firmware set.
- If all preflight checks pass in a future gated live run, the only activation write remains `1\n` to `/sys/kernel/boot_adsp/boot` once.
- No `tinymix`, `tinyplay`, PCM, HAL, adsprpc invoke/ioctl, `/dev/subsys_adsp` open, retry, unload, or playback path is added.

## Host Evidence Correction

- V2328 correctly blocked before activation, but the immediate `adsp.b12` discriminator was a false-negative in the V2327 preflight model.
- The private AUD-0 NON-HLOS FAT directory inventory lists `ADSP.B00`..`ADSP.B11` and `ADSP.B13`..`ADSP.B16`, plus `ADSP.MDT`; it does not list `ADSP.B12`.
- Therefore a complete stock ADSP image for this build is the sparse 16-segment set, not a contiguous 17-segment set.
- V2328 also showed `firmware_class.path=/mnt/vendor/firmware` while V2327 validated only `/vendor/firmware_mnt/image`; V2329 treats the effective firmware_class path as the write gate.

## Expected Live Discriminator

- If `/vendor/firmware_mnt/image` has the sparse ADSP set but `firmware_class.path` still points at `/mnt/vendor/firmware` without ADSP files, `audio adsp-boot-once` must refuse with `firmware-class-path-incomplete` and keep `activation_write_attempted=0`.
- A future AUD-2 activation attempt requires a separate, explicit serve-path fix or proof that the effective firmware_class path exposes the sparse ADSP set.

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

## Static Validation

- Source build: PASS.
- `file` on init binary: recorded by builder output.
- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2329_audio_adsp_fw_preflight.py`: PASS.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS (`996` tests).
- `git diff --check`: PASS.
