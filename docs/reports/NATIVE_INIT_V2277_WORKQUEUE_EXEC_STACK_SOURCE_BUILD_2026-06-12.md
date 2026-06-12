# Native Init V2277 Workqueue Execute Stack Source Build

## Summary

- Cycle: `V2277`
- Type: source/build-only rollbackable post-FWREADY workqueue execute_start stack/callsite oracle test boot.
- Decision: `v2277-workqueue-exec-stack-source-build-pass`
- Result: PASS
- Reason: V2276 made the V2275 workqueue `work->func` evidence classifiable and target-negative. V2277 packages a narrower workqueue `execute_start` stack sampler and the perf-regs/codeword sampler together so the next live run can classify worker call-stack/callsite context with same-boot codeword evidence.
- Manifest: `workspace/private/builds/native-init/v2277-workqueue-exec-stack/manifest.json`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2277_workqueue_exec_stack.img`
- Boot SHA256: `313a39b603296810dc44d8132c2c7db6c8fc790eb168a9ef9d94b20225baa18f`
- Init: `A90 Linux init 0.9.275 (v2277-workqueue-exec-stack)`
- Helper marker: `a90_android_execns_probe v433` (binary marker string: `a90_android_execns_probe v433`)
- Helper SHA256: `9772717fcf22bbdaec47348362107050899c6e026dbf4d670ebe693726c24e64`
- Workqueue sampler ramdisk path: `/bin/a90_bpf_workqueue_exec_stack_sample_ring`
- Workqueue sampler SHA256: `978e3406d4223d6f726d02ee2be041e2d7aa1f8934b0a4f21b889cd5c6e7d5b5`
- Codeword sampler ramdisk path: `/bin/a90_bpf_perf_regs_codeword_sample_ring`
- Codeword sampler SHA256: `3a16efc217eafeacbcc95a5e6005d0abce02e89ab52ed537df1fc2b193ca3dd7`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`
- Kept from V2237: service-object-visible route, post-FWREADY `boot_wlan`, firmware_class feeder, and strict supplicant terminate polling.
- Added for this build only: `A90_WIFI_TEST_BOOT_WORKQUEUE_EXEC_STACK_SAMPLER=1`, the inherited bounded workqueue sampler supervisor slot, `A90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_SAMPLER=1`, and ramdisk-local workqueue-stack/codeword BPF helpers.
- Capture contract: start both samplers before `append_post_fw_ready_boot_wlan_trigger`; observe `workqueue_execute_start` stacks for 45000 ms into `/cache/native-init-v2277-workqueue-exec-stack.log`, and sample perf regs/codewords for 45000 ms into `/cache/native-init-v2277-tail-perf-regs-codeword.log`. The live classifier should apply the V2276 bounded UAO-patch-aware same-boot slide rule.
- Next live use: V2278 should flash this image, collect the helper result plus both sampler logs, roll back to the selected baseline, verify selftest `FAIL=0`, and classify stack/callsite frames against the same-boot codeword evidence.

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
- `-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_DURATION_MS=45000`
- `-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_PERIOD_NS=1000000`
- `-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_PRINT_LIMIT=1024`
- `-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_WAIT_MS=60000`
- `-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_OUTPUT_PATH="/cache/native-init-v2277-tail-perf-regs-codeword.log"`
- `-DA90_WIFI_TEST_BOOT_TAIL_PERF_REGS_CODEWORD_HELPER_PATH="/bin/a90_bpf_perf_regs_codeword_sample_ring"`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_EXEC_STACK_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_SAMPLER=1`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_DURATION_MS=45000`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_PRINT_LIMIT=512`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_WAIT_MS=60000`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_OUTPUT_PATH="/cache/native-init-v2277-workqueue-exec-stack.log"`
- `-DA90_WIFI_TEST_BOOT_WORKQUEUE_FWCLASS_FUNC_HELPER_PATH="/bin/a90_bpf_workqueue_exec_stack_sample_ring"`

## Safety Scope

This build script performed host-side source/build work only. The new combined route attaches a read-only BPF tracepoint program to `workqueue_execute_start` and a read-only BPF perf-event program for codeword sampling; both store evidence in BPF maps. It does not write tracefs controls, execute `probe_write_user`, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping externally, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
