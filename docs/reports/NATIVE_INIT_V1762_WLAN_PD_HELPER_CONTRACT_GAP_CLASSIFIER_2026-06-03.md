# Native Init V1762 WLAN-PD Helper Contract-gap Classifier

## Summary

- Cycle: `V1762`
- Type: source-only helper contract-gap classifier
- Decision: `v1762-helper-needs-new-narrow-service-object-mode-source-pass`
- Label: `new-narrow-service-object-mode-needed`
- Result: PASS
- Reason: current helper has V1736 SM-route and peripheral uprobes, but its PM route is a broad pm-trio path already falsified by V1686; no narrow service-object-visible mode exists
- Evidence: `tmp/wifi/v1762-wlan-pd-helper-contract-gap-classifier`

## Source Facts

- Helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- Execns version marker: `a90_android_execns_probe v329`
- V1761 service-object gap input: `true`
- V1736 WLFW SM route input: `true`
- V1686 broad PM route regression input: `true`
- V1736 SM route mode present: `true`
- PM service-window mode present: `true`
- PM service-window mode is broad PM trio: `true`
- PM route order starts `pm_proxy_helper,per_mgr,per_proxy` before CNSS: `true`
- Narrow service-object-visible mode present: `false`
- Peripheral uprobe summary present: `true`
- Manager register TX probe present: `true`
- Null PeripheralManager branch probe present: `true`

## Existing Orders

- SM route order: `servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,cnss_daemon,service-window-trigger-summary`
- PM route order: `servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,pm_proxy_helper,per_mgr,per_proxy,subsys_modem_holder,cnss_diag,cnss_daemon,pm-service-window-trigger-summary`

## Interpretation

- The helper already has the V1736 SM route and the uprobe markers needed to detect the PM service-object branch.
- The only existing WLAN-PD PM service-window route is the broad PM trio path; V1686 already showed that path regresses WLFW/request progress.
- Therefore the next implementation unit should not reuse the broad PM service-window mode as-is.
- The missing source unit is a narrow mode that preserves V1736 ordering and only proves the PeripheralManager service-object visibility/PM register-vote contract before measuring `requested_wlanmdsp`.

## Next

- V1763 should be source/build-only: add a fail-closed helper mode for `service-object-visible + V1736 SM route` with explicit output keys for service object non-null, `asInterface`, manager register TX, PM vote/log evidence, `requested_wlanmdsp`, WLFW service 69, and `wlan0`.
- The new mode must not start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, external ping, `boot_wlan`, restart-PD, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, PCI rescan, platform bind/unbind, firmware writes, or partition writes.
- Live remains blocked until source/build artifact sanity proves the new mode is bounded and rollbackable.

## Safety Scope

This classifier is source-only. It performs no device contact, flash, reboot, actor start, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, or partition write.
