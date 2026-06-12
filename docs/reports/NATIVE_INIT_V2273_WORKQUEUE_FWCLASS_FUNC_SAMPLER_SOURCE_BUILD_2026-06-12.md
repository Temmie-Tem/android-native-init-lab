# Native Init V2273 Workqueue Firmware Class Function Sampler Source Build

## Summary

- Cycle: `V2273`
- Type: source/build-only rollbackable post-FWREADY workqueue function-pointer oracle test boot.
- Decision: `v2273-workqueue-fwclass-func-sampler-source-build-pass`
- Result: PASS
- Reason: V2272 selected T1 as the next independent oracle: observe queued/executed workqueue function pointers around the `boot_wlan` and firmware_class feeder window, then classify them offline against the same-boot exact slide/codeword evidence.
- Manifest: `workspace/private/builds/native-init/v2273-workqueue-fwclass-func-sampler/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2273_workqueue_fwclass_func_sampler.img`
- Boot SHA256: `ac9bd247f37308b91fc8d63397e3b34704268d96026268b2b7b11e9bbcbe6ba6`
- Init: `A90 Linux init 0.9.273 (v2273-workqueue-fwclass-func-sampler)`
- Helper marker: `a90_android_execns_probe v431` (binary marker string: `a90_android_execns_probe v431`)
- Helper SHA256: `2f28c91401811af357602de6a3f339a5ca73ba0e74aa7085e46444f055252628`
- Workqueue sampler ramdisk path: `/bin/a90_bpf_workqueue_func_sample_ring`
- Workqueue sampler SHA256: `4f3250d996de5156bb43bcc2844e5cb429b8478cc1aaf32244281d58e8f6f524`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Kept from V2237: service-object-visible route, post-FWREADY `boot_wlan`, firmware_class feeder, and strict supplicant terminate polling.
- Added for this build only: `A90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_SAMPLER=1` and ramdisk-local `/bin/a90_bpf_workqueue_func_sample_ring`.
- Capture contract: start before `append_post_fw_ready_boot_wlan_trigger`, observe `workqueue_queue_work` and `workqueue_execute_start` for 45000 ms, print up to 2048 samples, write `/cache/native-init-v2273-workqueue-fwclass.log`, then classify samples offline after the live handoff.
- Next live use: V2274 should flash this image, collect the helper result plus the workqueue log, roll back to the selected baseline, verify selftest `FAIL=0`, and classify function pointers against the same-boot exact slide/codeword evidence.

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
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_DURATION_MS=45000`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_PRINT_LIMIT=2048`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_WAIT_MS=60000`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_OUTPUT_PATH="/cache/native-init-v2273-workqueue-fwclass.log"`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_HELPER_PATH="/bin/a90_bpf_workqueue_func_sample_ring"`

## Safety Scope

This build script performed host-side source/build work only. The new sampler attaches read-only BPF tracepoint programs to workqueue events and stores tracepoint-record scalar fields in BPF maps. It does not write tracefs controls, execute `probe_write_user`, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping externally, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
