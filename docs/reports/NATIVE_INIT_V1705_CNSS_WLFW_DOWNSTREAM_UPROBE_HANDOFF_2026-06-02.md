# Native Init V1705 CNSS WLFW Downstream Uprobe Handoff

## Summary

- Cycle: `V1705`
- Type: one-run rollbackable CNSS WLFW downstream tracefs uprobe classifier
- Decision: `v1705-wlfw-worker-thread-missing-after-wlfw-start-rollback-pass`
- Result: `PASS`
- Evidence: `tmp/wifi/v1705-cnss-wlfw-downstream-uprobe-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- output label: `cnss-output-still-invisible`
- downstream non-log label: `wlfw-worker-thread-missing-after-wlfw-start`
- legacy firmware-serve label: `firmware-not-requested`
- property lookup all_match: `1`
- cnss-daemon running: `1`
- tftp running: `1`
- companion order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,cnss_daemon,cnss-output-visibility-summary`

## Downstream Trace Targets

- `wlfw_start` offset `0xec00` hit_count `1` registered/enabled `1` / `1`
  first_hit: `cnss-daemon-559   [003] ....     3.548774: wlfw_start: (0x556ff80c00)`
- `wlfw_service_request` offset `0xd9fc` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_ind_register_qmi` offset `0xf32c` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `wlfw_cap_qmi` offset `0xf460` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`
- `dms_service_request` offset `0xe808` hit_count `0` registered/enabled `1` / `1`
  first_hit: `none`

## Existing Control Evidence

- tracefs path/available: `/sys/kernel/debug/tracing` / `1`
- aggregate wlfw_start hit count: `1`
- aggregate first hit line: `cnss-daemon-559   [003] ....     3.548774: wlfw_start: (0x556ff80c00)`
- maps text seen / runtime PC: `1` / `0x556ff80c00`
- socket/kmsg fd counts: `10` / `0`
- MHI pipe fd count / ks process count: `0` / `0`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Interpretation

- This V1705 label means `wlfw_start` was entered, but the `wlfw_service_request` worker entry did not run during the bounded window.
- The next unit should classify the `wlfw_start` internal branch around `pthread_create@0xecf0` before chasing WLFW QMI or BDF.
- `wlfw_service_request` without QMI send targets means the worker started but is waiting before the first WLFW QMI sync call.
- `wlfw_ind_register_qmi` means cnss-daemon reached the first concrete WLFW QMI send path.
- `wlfw_cap_qmi` means WLFW indication registration advanced to capability query; only then should BDF/REGDB transfer be considered.
- This classifier does not start Wi-Fi HAL, scan, connect, or external network tests.
