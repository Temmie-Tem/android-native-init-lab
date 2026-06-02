# Native Init V1732 CNSS Output and WLAN-PD State-up Correction

## Summary

- Cycle: `V1732`
- Type: host-only correction/current-evidence classifier
- Decision: `v1732-cnss-output-artifact-wlan-pd-stateup-gap-pass`
- Result: `PASS`
- Evidence: `tmp/wifi/v1732-cnss-output-stateup-correction`

## Corrections Fixed

- Retract the QCACLD-register premise: `boot_wlan` / QCACLD driver registration is not a WLFW server trigger.
- Treat native `wlfw_start` log absence as a measurement artifact unless non-log control-flow evidence also misses `wlfw_start`.
- Stop PM/service-window actor expansion for this branch. The current evidence already reaches `wlfw_start` and `wlfw_service_request` without PM trio or `boot_wlan`.

## Output Visibility Branch

- V1725 strict output label: `cnss-output-still-invisible`
- V1725 property lookup matched: `1`
- V1725 kmsg property: expected `1`, value `1`, match `1`
- V1725 debug property: expected `4`, value `4`, match `1`
- V1727 non-log label: `wlfw-worker-thread-started-waiting-for-qmi-service`
- V1727 `wlfw_start` / `wlfw_service_request` / worker-create-success hits: `1` / `1` / `1`

Interpretation: the output-only path remains invisible, but non-log evidence proves `cnss-daemon` reaches `wlfw_start`, creates the `wlfw_service_request` worker, and then waits for WLFW QMI. The missing dmesg/log line is not a reason to add `boot_wlan`, PM trio, or more pre-CNSS actors.

## Android-good State-up Reference

- `wlfw_start`: `8.344747` s
- `wlfw_service_request`: `8.395398` s
- WLAN-PD service-notifier UP: `9.519168` s
- ICNSS QMI connected: `9.521544` s
- first BDF request: `9.59014` s
- `wlan0`: `14.912363` s
- request-to-WLAN-PD-UP delta: `1123.77` ms
- WLAN-PD-UP-to-ICNSS-QMI delta: `2.376` ms

## Native Current State

- V1731 decision: `v1731-late-listener-uninit-no-indication-rollback-pass`
- service-window label: `wlfw-start-reached`
- non-log label: `wlfw-worker-thread-started-waiting-for-qmi-service`
- late service-notifier endpoint: `endpoint-found` node `0` port `2`
- late listener response: `listener-response-success` state `0x7fffffff` / `uninit`
- late indication seen: `0`
- WLFW service 69 seen: `0`
- requested `wlanmdsp`: `0`

## Fixed Classification

- Label: `wlfw-start-reached-wlan-pd-uninit-downstream-block`
- Missing surface: `modem-side-wlan-pd-state-up-and-wlfw-service69-publication`

Android reaches WLAN-PD UP about one second after `wlfw_service_request`; native reaches the same `wlfw_service_request` worker but the late service-notifier listener still reports `UNINIT`, receives no indication, sees no WLFW service 69, and sees no `wlanmdsp` request. The blocker is therefore modem-side WLAN-PD state-up / image-load request publication, not CNSS output visibility, not QCACLD registration, and not PM-service actor ordering.

## Checks

- `v1681_retracted_by_new_evidence`: `True`
- `v1725_output_branch_ran`: `True`
- `v1725_properties_matched`: `True`
- `v1727_nonlog_wlfw_reached`: `True`
- `v1731_worker_created`: `True`
- `v1729_late_endpoint_found`: `True`
- `v1731_late_listener_uninit`: `True`
- `v1731_no_indication`: `True`
- `v1731_no_service69`: `True`
- `v1731_no_wlanmdsp`: `True`
- `android_good_state_up_chain`: `True`

## Next Gate

- Do not repeat output-visibility, service-manager, PM-trio, `boot_wlan`, eSoC/RC1, or timing-window variants.
- Next useful unit: host-only V1733 modem-side WLAN-PD state-up trigger classifier from Android-good/current native evidence, focused on what causes the modem to move `msm/modem/wlan_pd` from `UNINIT` to `UP` and request or publish WLFW service 69.
- A future live gate should only run after V1733 identifies a concrete non-mutating trigger or observation point.

## Safety Scope

This script performed host-only analysis only. It did not contact the device, flash, reboot, start service-manager/PM actors, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
