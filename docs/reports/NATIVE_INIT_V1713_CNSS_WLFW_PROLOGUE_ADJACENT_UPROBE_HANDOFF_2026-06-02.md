# Native Init V1713 CNSS WLFW Prologue Adjacent Uprobe Handoff

## Summary

- Cycle: `V1713`
- Type: one-run rollbackable CNSS `wlfw_start` adjacent-prologue tracefs uprobe classifier
- Decision: `v1713-wlfw-start-optional-pm-init1-call-no-return-rollback-pass`
- Result: `PASS`
- Evidence: `tmp/wifi/v1713-cnss-wlfw-prologue-adjacent-uprobe-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- output label: `cnss-output-still-invisible`
- prologue non-log label: `wlfw-start-optional-pm-init1-call-no-return`
- legacy firmware-serve label: `firmware-not-requested`
- property lookup all_match: `1`
- cnss-daemon running: `1`
- tftp running: `1`
- companion order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,cnss_daemon,cnss-output-visibility-summary`

## Prologue Trace Targets

- `wlfw_start` offset `0xec00` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-561   [003] ....     3.577657: wlfw_start: (0x5568e5ac00)`
- `wlfw_service_request` offset `0xd9fc` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_ind_register_qmi` offset `0xf32c` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cap_qmi` offset `0xf460` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `dms_service_request` offset `0xe808` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_log_arg_severity` offset `0xec20` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-561   [003] ....     3.577682: wlfw_log_arg_severity: (0x5568e5ac20)`
- `wlfw_log_call` offset `0xec24` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-561   [003] ....     3.577687: wlfw_log_call: (0x5568e5ac24)`
- `wlfw_post_log_branch` offset `0xec28` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-561   [002] ....     3.588923: wlfw_post_log_branch: (0x5568e5ac28)`
- `wlfw_optional_pm_init1_call` offset `0xec34` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-561   [002] ....     3.588929: wlfw_optional_pm_init1_call: (0x5568e5ac34)`
- `wlfw_optional_pm_init1_return` offset `0xec38` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_optional_pm_init2_call` offset `0xec44` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_common_state_base` offset `0xec48` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cal_mutex_arg` offset `0xec50` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cal_mutex_null_attr` offset `0xec54` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cal_mutex_call` offset `0xec58` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cal_mutex_retcheck` offset `0xec5c` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cal_mutex_fail` offset `0xec60` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_mutex_call` offset `0xec78` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_mutex_retcheck` offset `0xec7c` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_mutex_fail` offset `0xec80` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cond_call` offset `0xec9c` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cond_retcheck` offset `0xeca0` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cond_fail` offset `0xeca4` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cond_rsp_call` offset `0xecbc` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cond_rsp_retcheck` offset `0xecc0` hit_count `0` registered/enabled `1` / `1`
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

## Control Evidence

- tracefs path/available: `/sys/kernel/debug/tracing` / `1`
- aggregate wlfw_start hit count: `1`
- aggregate first hit line: `cnss-daemon-561   [003] ....     3.577657: wlfw_start: (0x5568e5ac00)`
- maps text seen / runtime PC: `1` / `0x5568e5ac00`
- socket/kmsg fd counts: `10` / `0`
- MHI pipe fd count / ks process count: `0` / `0`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Interpretation

- This V1713 run distinguishes the `wlfw_start` entry-only gap from V1710.
- Actual result: `0xec20`, `0xec24`, `0xec28`, and `0xec34` all hit, while
  `0xec38`, `0xec44`, `0xec48`, `0xec50`, and `0xec58` stayed at `0`.
- Therefore `wlfw_start` returns from its unconditional log wrapper and then
  blocks inside the first optional setup call at `cnss-daemon+0xec34`, which
  calls `pm_init@0xc39c` with the zero-argument path active.
- `wlfw-start-log-call-no-return` means the unconditional log wrapper at `0xec24` is the first live blocker.
- `wlfw-start-post-log-branch-no-common-path` or optional setup labels indicate the function returned from logging but did not reach the common state setup.
- `wlfw-start-cal-mutex-call-no-return` moves the blocker back to the first pthread init call.
- The next unit should statically map `pm_init@0xc39c` and then decide whether
  a bounded live probe inside that function is needed. Do not add PM/service
  actors until that internal gate is classified.
- This classifier does not start Wi-Fi HAL, scan, connect, or external network tests.
