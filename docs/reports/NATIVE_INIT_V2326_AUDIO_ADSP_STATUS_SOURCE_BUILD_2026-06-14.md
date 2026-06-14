# Native Init V2326 Audio ADSP Status Source Build

## Summary

- Cycle: `V2326`
- Track: audio AUD-2 preparation, source/build-only.
- Decision: `v2326-audio-adsp-status-source-build-pass`
- Result: PASS
- Device flash: `no`.
- Device action: `none`.
- Manifest: `workspace/private/builds/native-init/v2326-audio-adsp-status/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2326_audio_adsp_status.img`
- Boot SHA256: `49c6e978e564dea605a95cb61da405664915ddf5f90184815378a9c5c358fafd`
- Init: `A90 Linux init 0.9.288 (v2326-audio-adsp-status)`
- Helper marker: `a90_android_execns_probe helper-v427` (binary marker string: `a90_android_execns_probe v427`)
- Helper SHA256: `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910`

## Change

- Adds the native-init command `audio [adsp-status|status]`.
- The command is read-only: it reports firmware-class path, `/sys/kernel/boot_adsp/boot` metadata, ADSP firmware visibility, remoteproc/RPMSG/FastRPC/sound class counts, `/proc/asound/cards`, and relevant device-node metadata.
- The command reports `audio.status.activation_write_attempted=0` and `audio.status.audio_playback_attempted=0` by construction.
- No `audio adsp-boot-once`, `tinymix`, `tinyplay`, PCM, HAL, adsprpc invoke/ioctl, or `/dev/subsys_adsp` open path is added.

## Safety Boundary

- This is not AUD-2 live execution. It only prepares the read-only preflight surface that AUD-2 would use after explicit operator approval.
- No ADSP activation write is implemented or run.
- No flash was performed by this source-build unit.
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
- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2326_audio_adsp_status.py`: PASS.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: PASS (`996` tests).
- `git diff --check`: PASS.
