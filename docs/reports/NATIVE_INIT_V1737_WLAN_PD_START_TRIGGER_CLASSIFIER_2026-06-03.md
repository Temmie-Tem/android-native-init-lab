# Native Init V1737 WLAN-PD Start Trigger Classifier

## Summary

- Cycle: `V1737`
- Type: host-only WLAN-PD start trigger classifier
- Decision: `v1737-modem-side-wlan-pd-start-trigger-gap-pass`
- Result: `PASS`
- Label: `modem-side-wlan-pd-start-trigger-gap`
- Evidence: `tmp/wifi/v1737-wlan-pd-start-trigger-classifier`

## Closed Premises

- service-locator domain: `msm/modem/wlan_pd` instance `180`
- listener model: Android V833 positive-control returns WLAN-PD `UP` for the same listener request
- CNSS static path: `wlfw_service_request` mapped, indication/capability QMI calls downstream mapped: `True`
- firmware serve route: V1680 label `firmware-not-requested`, tftp running `1`, requested `wlanmdsp` `0`

## Native V1736

- decision: `v1736-wlfw-start-reached-downstream-block-rollback-pass`
- service-window label: `wlfw-start-reached`
- non-log label: `wlfw-worker-thread-started-waiting-for-qmi-service`
- `wlfw_start` / `wlfw_service_request` / worker success hits: `1` / `1` / `1`
- first `wlfw_start` / `wlfw_service_request` trace times: `4.164112` s / `9.212816` s
- WLFW indication-register QMI / capability QMI hits: `0` / `0`
- late listener: `listener-response-success`, state `uninit`, indication `0`, hold `15015` ms
- WLFW service 69 / requested `wlanmdsp`: `0` / `0`
- observer monotonic ms: `50225`

## Android-good Delta

- V1734 Android `wlfw_service_request` to WLAN-PD UP: `1123.77` ms
- V1734 Android WLAN-PD UP to ICNSS QMI: `2.376` ms
- Native now reaches the same CNSS worker but still never sees WLAN-PD UP, WLFW service 69, or a `wlanmdsp` request.

## Classification

V1736 confirms the latest correction: missing native `wlfw_start` logs were a measurement artifact. `cnss-daemon` reaches `wlfw_start`, starts `wlfw_service_request`, and creates the worker. The block is after CNSS worker creation but before WLFW QMI indication registration/capability calls, because WLFW service 69 never appears and WLAN-PD remains `UNINIT`.

The remaining start trigger is modem-side: native has domain mapping, a valid service-notifier endpoint, tftp running, and internal modem reset/QRTR, but the modem never starts `msm/modem/wlan_pd` and never asks for `wlanmdsp.mbn`.

## Next Gate

- V1738 should be host-only/source-only first: classify the Android-good modem-side WLAN-PD start trigger surface before any mutation.
- Inputs should stay bounded to existing Android-good dmesg/trace evidence, ICNSS/CNSS source or disassembly, service-locator/servreg evidence, and firmware-serve evidence.
- Candidate outcomes: `pd-trigger-request-surface-identified`, `pd-trigger-is-modem-autoload-missing`, `pd-trigger-evidence-incomplete`.
- Do not add PM/service-window actors, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Checks

- `domain_mapping_present`: `True`
- `listener_model_positive_control_up`: `True`
- `firmware_serve_route_not_requested`: `True`
- `cnss_downstream_static_mapped`: `True`
- `android_good_up_after_wlfw_request`: `True`
- `native_cnss_worker_reached`: `True`
- `native_waits_before_wlfw_qmi`: `True`
- `native_wlan_pd_stays_uninit`: `True`
- `native_no_wlfw69_or_firmware_request`: `True`
- `hard_stops_preserved`: `True`

## Safety Scope

This script performed host-only analysis only. It did not contact the device, flash, reboot, send QMI payloads, start services, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
