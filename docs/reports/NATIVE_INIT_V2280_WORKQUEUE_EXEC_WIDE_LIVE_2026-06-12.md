# Native Init V2280 Workqueue Execute Wide Live

## Summary

- Cycle: `V2280`
- Type: rollbackable live validation of the V2279 wide workqueue execute_start and same-boot codeword observer.
- Decision: `v2280-workqueue-exec-wide-live-pass-workqueue-exec-wide-no-target-hit`
- Result: `PASS`
- Reason: V2279 wide workqueue execute-start and codeword artifacts were collected and classified; rollback selftest fail=0 passed
- Execute mode: `True`
- Evidence: `workspace/private/runs/kernel/v2280-workqueue-exec-wide-live-20260612-184403`
- Track: T1 kernel observation; no downgrade to T2/T3.

## Images

- Test image: `workspace/private/inputs/boot_images/boot_linux_v2279_workqueue_exec_wide.img`
- Test SHA256: `bfe6d2bb4f2e60e83b4b5ff104e153825bd10aa012afc1f5b4ee75909e57d541`
- Test version: `A90 Linux init 0.9.276 (v2279-workqueue-exec-wide)`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
- Rollback SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Rollback version: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`

## Live Evidence

- Preflight baseline verified: `True` selftest fail=0: `True`
- V2279 flash OK: `True`
- V2279 health: version=`True` status=`True` selftest_fail0=`True`
- Rollback OK: `True` via `from-native`
- Rollback health: version=`True` status=`True` selftest_fail0=`True`
- Classification: `workqueue-exec-wide-no-target-hit`
- Workqueue samples: `6281` stats=`{'total': 6281, 'stored': 6281, 'overflow': 0}`
- Codeword slide: accepted=`True` slide=`0xe4ef4` reason=`lr_exact_single_pc_mismatch` patch_aware=`True`
- Target hits: total=`0` function=`0` stack=`0`
- Helper result: supervisor=`wlan0-ready` exit=`0` timed_out=`0` wlan0_present=`1`

## Workqueue Wide Classification

- Workqueue sampler result: `v2279-workqueue-exec-wide-sample-ring-complete`
- Top function symbols: `[('proc_sys_call_handler', 3139), ('diagchar_ioctl', 944), ('smb1390_cp_slave_get_prop', 450), ('register_notif_listener', 427), ('msm_ssusb_qmp_clamp_enable', 289), ('shmem_link', 142), ('dma_find_channel', 90), ('sdev_show_evt_lun_change_reported', 52), ('sdev_store_evt_lun_change_reported', 52), ('ufs_qcom_phy_clk_state', 52), ('blkcg_policy_unregister', 49), ('tty_unregister_driver', 49), ('shmem_unlink', 45), ('autosuspend_delay_ms_store', 36), ('elv_requeue_request', 34), ('_debug_stats_read', 31), ('glink_spss_reset', 31), ('show_nr_prev_assist_thresh', 31), ('ufs_qcom_dump_dbg_regs', 31), ('ufshcd_system_suspend', 31), ('update_req_stats', 31), ('enable_show', 22), ('enable_store', 22), ('schedtune_cpu_update', 22)]`
- Top stack symbols: `[('sys_prctl', 1022), ('SyS_getcpu', 511), ('do_sp_pc_abort', 511), ('pid_vnr', 511)]`
- Function target hits: `[]`
- Stack target hits: `[]`

## Interpretation

- The paired wide/codeword oracle was classifiable, but no execute_start function or printed stack frame intersected the firmware_class/qcacld-HDD target set.
- This closes the V2278 overflow caveat for scalar `function` coverage: all `6281` observed execute_start rows were stored/printed with `overflow=0` and no target function hit. Stack evidence remains a bounded `512`-sample prefix, not a full-stack path-negative.

## Safety Scope

- Flash path is limited to boot partition via `native_init_flash.py`.
- Rollback target is V2237, with post-rollback `version`/`status`/`selftest fail=0` verification.
- Collection uses read-only `cat` through the native bridge after the helper window.
- This run does not use Wi-Fi scan/connect, credentials, DHCP/routes, external ping, `probe_write_user`, tracefs control writes, eSoC/PCIe/GDSC/PMIC/GPIO paths, platform bind/unbind, or `sda29` writes.
- The only target partition writes are the bounded test boot flash and rollback boot flash.
