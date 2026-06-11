# Native Init V2229 Service-Object-Visible Handoff Runner

## Summary

- Cycle: `V2229`
- Type: rollbackable service-object-visible handoff runner; default execution is host-only dry-run.
- Decision: `v2229-service-object-visible-helper-parsed-rollback-pass`
- Result: `PASS`
- Reason: V2228 helper artifacts were collected, parsed by V2220, and rollback selftest fail=0
- Execute mode: `True`
- Evidence: `workspace/private/runs/kernel/v2229-live-20260612-080114`

## Images

- Test image: `workspace/private/inputs/boot_images/boot_linux_v2228_service_object_visible_observer.img`
- Test SHA256: `195d23e02cfd54bfb2c82aba3bba47ec108bbeac7d3f8d4b16ef18d84b32294a`
- Test version: `A90 Linux init 0.9.264 (v2228-service-object-visible-observer)`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img`
- Rollback SHA256: `f54becb2b720ad198413c2a0089912626ca295c79a96f13e0921cf4f05b39f51`
- Rollback version: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`

## Live Contract

- Live mode requires `--execute` plus the exact confirmation token.
- Live sequence: V2222 preflight -> flash V2228 -> collect `/cache/native-init-wifi-test-boot-v2228-*` -> V2220 parser -> rollback V2189 -> selftest fail=0.
- Collection is read-only after boot; it uses `cat` over the native bridge and the helper-owned trace output.

## Live Evidence

- Rollback OK: `True`
- Rollback selftest fail=0: `True`
- Parser decision: `v2220-helper-summary-parser-validated-existing-hit-current-nohit`
- Parser pass: `True`
- Parser hits: total=`654` hit_events=`121` key_hit_events=`8`
- Helper diagnosis: `helper-artifacts-present`
- Helper result: supervisor=`helper-complete-no-wlan0` exit=`0` timed_out=`0` wlan0_present=`0`

## Nonlog Control-Flow Summary

- Classifier: `wlfw-worker-thread-started-qmi-cap-sent`
- `pm_init_pm_client_register_call`: hits=`1`
- `pm_init_pm_client_register_retcheck`: hits=`1`
- `periph_default_service_manager_call`: hits=`1`
- `periph_manager_name_string16_call`: hits=`1`
- `wlfw_bdf_send_ret`: hits=`9`
- `wlfw_bdf_result_log`: hits=`2`
- `wlfw_worker_done_signal`: hits=`1`

## Service-Object Snapshot

- Classifier: `provider-visible-modem-holder-regression`
- Service readiness: vnd=`1` pm_proxy=`1` per_mgr=`1` provider_seen=`1`
- Runtime children: tftp=`1` cnss_daemon=`1` modem_holder_opened=`0`
- Request snapshot: wlfw_start=`1` wlfw_service_request=`1` service69=`0` requested_wlanmdsp=`0` wlan0=`0`

## WLFW Edge Summary

- `uprobe:wlfw_start`: hits=`1` first_ts=`6.754557`
- `uprobe:wlfw_service_request`: hits=`1` first_ts=`6.779672`
- `uprobe:wlfw_cap_qmi`: hits=`1` first_ts=`67.48452`
- `uprobe:wlfw_bdf_entry`: hits=`2` first_ts=`67.529402`
- `uprobe:wlfw_bdf_send_ret`: hits=`9` first_ts=`67.544413`
- `uprobe:wlfw_bdf_result_log`: hits=`2` first_ts=`67.545844`
- `uprobe:wlfw_worker_done_signal`: hits=`1` first_ts=`67.561877`
- `uprobe:wlfw_worker_post_done_wait`: hits=`1` first_ts=`67.561882`
- `libqmi_uprobe:libqmi_loop_client_init_ret`: hits=`2` first_ts=`67.293134`

## Live Diagnosis

- V2228 solved the V2227 `defaultServiceManager()` stall: CNSS reached PM registration, `wlfw_service_request`, WLFW capability QMI, and BDF send/result edges.
- The helper still completed with `wlan0_present=0`; the remaining blocker is now after BDF/QMI progress, not the service-manager registration gate.
- Service-object snapshot label: `provider-visible-modem-holder-regression`; it reports service/provider readiness but no `wlan0` at helper end.
- Next unit: extend/target the post-BDF window and instrument FW_READY / ICNSS / qcacld netdev creation rather than reworking service-manager or WLFW request offsets.

## Safety Scope

- Dry-run does not flash, reboot, write device partitions, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping, attach BPF, execute `probe_write_user`, or write tracefs controls.
- Live mode flashes only the approved rollbackable V2228 test boot and V2189 rollback image.
- It does not use Wi-Fi HAL scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC/eSoC/PCI paths, platform bind/unbind, or `sda29` writes.
