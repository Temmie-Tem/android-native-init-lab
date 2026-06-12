# Native Init V2278 Workqueue Execute Stack Live

## Summary

- Cycle: `V2278`
- Type: rollbackable live validation of the V2277 workqueue execute_start stack/callsite and same-boot codeword observer.
- Decision: `v2278-workqueue-exec-stack-live-pass-workqueue-exec-stack-no-target-hit-partial-coverage`
- Result: `PASS`
- Reason: V2277 workqueue execute-start stack and codeword artifacts were collected and classified; rollback selftest fail=0 passed
- Execute mode: `True`
- Evidence: `workspace/private/runs/kernel/v2278-workqueue-exec-stack-live-20260612-181524`
- Track: T1 kernel observation; no downgrade to T2/T3.

## Images

- Test image: `workspace/private/inputs/boot_images/boot_linux_v2277_workqueue_exec_stack.img`
- Test SHA256: `313a39b603296810dc44d8132c2c7db6c8fc790eb168a9ef9d94b20225baa18f`
- Test version: `A90 Linux init 0.9.275 (v2277-workqueue-exec-stack)`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
- Rollback SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Rollback version: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`

## Live Evidence

- Preflight baseline verified: `True` selftest fail=0: `True`
- V2277 flash OK: `True`
- V2277 health: version=`True` status=`True` selftest_fail0=`True`
- Rollback OK: `True` via `from-native`
- Rollback health: version=`True` status=`True` selftest_fail0=`True`
- Classification: `workqueue-exec-stack-no-target-hit-partial-coverage`
- Workqueue samples: `512` stats=`{'total': 6237, 'stored': 1024, 'overflow': 5213}`
- Codeword slide: accepted=`True` slide=`0x124ef4` reason=`exact_pc_lr_codeword_match` patch_aware=`False`
- Target hits: total=`0` function=`0` stack=`0`
- Helper result: supervisor=`wlan0-ready` exit=`0` timed_out=`0` wlan0_present=`1`

## Workqueue Stack Classification

- Workqueue sampler result: `v2277-workqueue-exec-stack-sample-ring-complete`
- Top function symbols: `[('proc_sys_call_handler', 286), ('diagchar_ioctl', 63), ('smb1390_cp_slave_get_prop', 42), ('register_notif_listener', 29), ('shmem_link', 9), ('dma_find_channel', 6), ('elv_requeue_request', 6), ('sdev_show_evt_lun_change_reported', 6), ('sdev_store_evt_lun_change_reported', 6), ('ufs_qcom_phy_clk_state', 6), ('blkcg_policy_unregister', 4), ('dek_create_sysfs_asym_alg', 4), ('glink_spss_reset', 4), ('show_nr_prev_assist_thresh', 4), ('ufs_qcom_dump_dbg_regs', 4), ('update_req_stats', 4), ('_debug_stats_read', 3), ('autosuspend_delay_ms_store', 3), ('shmem_unlink', 3), ('ufshcd_system_suspend', 3), ('dd_end_io', 2), ('enable_show', 2), ('enable_store', 2), ('scan_positives', 2)]`
- Top stack symbols: `[('sys_prctl', 1024), ('SyS_getcpu', 512), ('do_sp_pc_abort', 512), ('pid_vnr', 512)]`
- Function target hits: `[]`
- Stack target hits: `[]`

## Interpretation

- The paired stack/codeword oracle was classifiable, but no execute_start function or printed stack frame intersected the firmware_class/qcacld-HDD target set.
- This is independent negative evidence relative to the V2275 `work->func` result, but it still only covers the printed V2277 workqueue window.
- Coverage caveat: the helper printed `512` samples, stored `1024`, and overflowed `5213` additional events. Treat this as a printed-window negative, not as a full workqueue path-negative. Do not rerun the same V2277 image; the next oracle must raise capacity/print coverage or filter earlier on-device.

## Safety Scope

- Flash path is limited to boot partition via `native_init_flash.py`.
- Rollback target is V2237, with post-rollback `version`/`status`/`selftest fail=0` verification.
- Collection uses read-only `cat` through the native bridge after the helper window.
- This run does not use Wi-Fi scan/connect, credentials, DHCP/routes, external ping, `probe_write_user`, tracefs control writes, eSoC/PCIe/GDSC/PMIC/GPIO paths, platform bind/unbind, or `sda29` writes.
- The only target partition writes are the bounded test boot flash and rollback boot flash.
