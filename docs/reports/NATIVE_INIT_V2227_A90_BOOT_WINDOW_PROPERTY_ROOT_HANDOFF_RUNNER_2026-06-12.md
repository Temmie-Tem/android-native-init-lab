# Native Init V2227 A90 Boot-Window Handoff Runner

## Summary

- Cycle: `V2227`
- Type: rollbackable boot-window handoff runner; default execution is host-only dry-run.
- Decision: `v2227-boot-window-helper-parsed-rollback-pass`
- Result: `PASS`
- Reason: V2226 helper artifacts were collected, parsed by V2220, and rollback selftest fail=0
- Execute mode: `True`
- Evidence: `workspace/private/runs/kernel/v2227-live-wait2-20260612-073623`

## Images

- Test image: `workspace/private/inputs/boot_images/boot_linux_v2226_a90_boot_window_property_root.img`
- Test SHA256: `1f1dd7a12cfddf393e537bd96bc6efe4ecc4b6f809b58e071f60a21bec5c096d`
- Test version: `A90 Linux init 0.9.263 (v2226-a90-boot-window-property-root)`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img`
- Rollback SHA256: `f54becb2b720ad198413c2a0089912626ca295c79a96f13e0921cf4f05b39f51`
- Rollback version: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`

## Live Contract

- Live mode requires `--execute` plus the exact confirmation token.
- Live sequence: V2222 preflight -> flash V2226 -> collect `/cache/native-init-wifi-test-boot-v2226-*` -> V2220 parser -> rollback V2189 -> selftest fail=0.
- Collection is read-only after boot; it uses `cat` over the native bridge and the helper-owned trace output.

## Live Evidence

- Rollback OK: `True`
- Rollback selftest fail=0: `True`
- Parser decision: `v2220-helper-summary-parser-validated-existing-hit-current-nohit`
- Parser pass: `True`
- Parser hits: total=`21` hit_events=`19` key_hit_events=`1`
- Helper diagnosis: `helper-artifacts-present`
- Helper result: supervisor=`helper-complete-no-wlan0` exit=`0` timed_out=`0` wlan0_present=`0`

## Nonlog Control-Flow Summary

- Classifier: `peripheral-default-service-manager-call-no-return`
- `pm_init_pm_client_register_call`: hits=`1`
- `pm_init_pm_client_register_retcheck`: hits=`0`
- `periph_default_service_manager_call`: hits=`1`
- `periph_manager_name_string16_call`: hits=`0`

## WLFW Edge Summary

- `uprobe:wlfw_start`: hits=`1` first_ts=`3.224034`
- `uprobe:wlfw_service_request`: hits=`0` first_ts=`None`
- `uprobe:wlfw_cap_qmi`: hits=`0` first_ts=`None`
- `uprobe:wlfw_bdf_entry`: hits=`0` first_ts=`None`

## Live Diagnosis

- V2226 fixed the property-root setup failure and the helper completed normally.
- The trace reached `wlfw_start`, entered the CNSS PM registration path, and called into `libperipheral_client`.
- Nonlog classifier: `peripheral-default-service-manager-call-no-return`; `periph_default_service_manager_call` hit, but the service-name/get-service edge did not.
- This matches the V2226 output-visibility route: service-manager/PM trio were intentionally not started in that route.
- Next unit: enable the service-manager + PM/service-object-visible route with the same property-root and observer stack, rather than chasing more WLFW offsets.

## Safety Scope

- Dry-run does not flash, reboot, write device partitions, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping, attach BPF, execute `probe_write_user`, or write tracefs controls.
- Live mode flashes only the approved rollbackable V2226 test boot and V2189 rollback image.
- It does not use Wi-Fi HAL scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC/eSoC/PCI paths, platform bind/unbind, or `sda29` writes.
