# Native Init V1708 CNSS WLFW Start Branch Uprobe Handoff

## Summary

- Cycle: `V1708`
- Type: one-run rollbackable CNSS WLFW start-branch tracefs uprobe classifier
- Decision: `v1708-wlfw-start-pthread-create-not-reached-rollback-pass`
- Result: `PASS`
- Evidence: `tmp/wifi/v1708-cnss-wlfw-start-branch-uprobe-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- output label: `cnss-output-still-invisible`
- branch non-log label: `wlfw-start-pthread-create-not-reached`
- legacy firmware-serve label: `firmware-not-requested`
- property lookup all_match: `1`
- cnss-daemon running: `1`
- tftp running: `1`
- companion order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,cnss_daemon,cnss-output-visibility-summary`

## Branch Trace Targets

- `wlfw_start` offset `0xec00` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-558   [003] ....     3.537398: wlfw_start: (0x558af93c00)`
- `wlfw_service_request` offset `0xd9fc` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_ind_register_qmi` offset `0xf32c` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cap_qmi` offset `0xf460` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `dms_service_request` offset `0xe808` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cal_mutex_fail` offset `0xec60` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_mutex_fail` offset `0xec80` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cond_fail` offset `0xeca4` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cond_rsp_fail` offset `0xecc4` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_dms_initialize_call` offset `0xecd4` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_dms_initialize_retcheck` offset `0xecd8` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_worker_pthread_create_call` offset `0xecf0` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_worker_pthread_create_failure` offset `0xecf8` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_worker_pthread_create_success` offset `0xeda0` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`

## Existing Control Evidence

- tracefs path/available: `/sys/kernel/debug/tracing` / `1`
- aggregate wlfw_start hit count: `1`
- aggregate first hit line: `cnss-daemon-558   [003] ....     3.537398: wlfw_start: (0x558af93c00)`
- maps text seen / runtime PC: `1` / `0x558af93c00`
- socket/kmsg fd counts: `10` / `0`
- MHI pipe fd count / ks process count: `0` / `0`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Interpretation

- This V1708 run classifies where `wlfw_start` stops before the expected `wlfw_service_request` worker entry.
- WLFW QMI/BDF remains downstream unless this run reaches the worker entry or later QMI call targets.
- `wlfw_dms_initialize_call` without `wlfw_worker_pthread_create_call` means the block is in DMS initialization before worker creation.
- `wlfw_worker_pthread_create_failure` means pthread_create returned nonzero and the worker was not created.
- `wlfw_worker_pthread_create_success` without worker entry means the create call returned success but the expected worker entry was not observed.
- This classifier does not start Wi-Fi HAL, scan, connect, or external network tests.
- V1708 actual result: only `wlfw_start@0xec00` hit; DMS init, pthread_create, worker entry, QMI, and all traced failure branches remained at hit count `0`.
- The next unit should trace the pre-DMS init sequence itself: call/return-check points around `pthread_mutex_init` and `pthread_cond_init` before `0xecd4`.
