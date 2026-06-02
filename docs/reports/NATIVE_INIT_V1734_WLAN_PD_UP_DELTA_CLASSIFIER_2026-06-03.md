# Native Init V1734 WLAN-PD UP Delta Classifier

## Summary

- Cycle: `V1734`
- Type: host-only Android-good/native delta classifier
- Decision: `v1734-wlan-pd-up-delta-modem-pd-start-gap-pass`
- Result: `PASS`
- Evidence: `tmp/wifi/v1734-wlan-pd-up-delta-classifier`

## Android-good Reference

- service-notifier 180 server: `7.0987` s
- `wlfw_start`: `8.344747` s
- `wlfw_service_request`: `8.395398` s
- WLAN-PD UP indication: `9.519168` s
- ICNSS QMI connected: `9.521544` s
- first BDF request: `9.59014` s
- `wlan0`: `14.912363` s
- service180-to-`wlfw_start`: `1246.047` ms
- `wlfw_service_request`-to-WLAN-PD-UP: `1123.77` ms
- WLAN-PD-UP-to-ICNSS-QMI: `2.376` ms

## Native Current Delta

- V1732 fixed label: `wlfw-start-reached-wlan-pd-uninit-downstream-block`
- V1732 missing surface: `modem-side-wlan-pd-state-up-and-wlfw-service69-publication`
- V1727 non-log label: `wlfw-worker-thread-started-waiting-for-qmi-service`
- V1727 `wlfw_start` / `wlfw_service_request` / worker hits: `1` / `1` / `None`
- V1731 `wlfw_start` / `wlfw_service_request` / worker hits: `1` / `1` / `1`
- V1731 late listener endpoint: `endpoint-found` node `0` port `2`
- V1731 late listener state: `0x7fffffff` / `uninit`
- V1731 indication seen: `0` after `15015` ms hold
- V1731 WLFW service 69: `0`
- V1731 requested `wlanmdsp`: `0`
- V1680 firmware-serve label: `firmware-not-requested`
- V1680 tftp running / requested `wlanmdsp` / served `wlanmdsp`: `1` / `0` / `0`
- V1731 modem reset / QRTR RX: `4.752437` s / `4.806768` s
- V1731 rmt_storage open count: `3`

## Classification

- Label: `modem-side-wlan-pd-start-gap`
- Next gate: `V1735 source-build timestamped internal-modem WLAN-PD observer; V1736 one-run read-only live`

Android-good reaches WLAN-PD UP about one second after `cnss-daemon` starts `wlfw_service_request`. Native reaches the same CNSS worker and brings the internal modem out of reset, but the late service-notifier listener still reports WLAN-PD `UNINIT`, no indication, no WLFW service 69, and no `wlanmdsp` request. V1680 also showed the firmware-serve route running but `firmware-not-requested` and no nonzero `wlanmdsp` at the observed served path. The remaining useful work is therefore an exact internal-modem PD-start observer, not another CNSS output, PM/service-window, `boot_wlan`, restart-PD, or eSoC/RC1 gate.

## Next Gate Contract

- Source/build-only first: add a timestamped internal-modem WLAN-PD observer that reuses the V1731 route and records the exact sequence around modem reset, service-notifier endpoint publication, `wlfw_service_request`, tftp/rmt activity, firmware path visibility, WLFW service 69, and WLAN-PD listener state.
- Live gate after source sanity: one rollbackable read-only run, no new actors, no active PD restart request, and no Wi-Fi HAL/scan/connect.
- Fixed labels: `pd-start-trigger-absent`, `pd-firmware-path-invisible`, `pd-state-up-service69`, `pd-state-up-no-service69`, `route-regression`.
- Stop after one label. Do not spin timing variants or add PM/QCACLD/eSoC actors from this result.

## Checks

- `android_stateup_chain_present`: `True`
- `android_service180_precedes_wlfw_start`: `True`
- `native_cnss_worker_reached`: `True`
- `native_late_listener_uninit`: `True`
- `native_no_late_indication`: `True`
- `native_no_wlfw69`: `True`
- `native_no_wlanmdsp_request`: `True`
- `native_modem_reset_and_qrtr_seen`: `True`
- `firmware_serve_route_not_requested`: `True`
- `served_wlanmdsp_not_nonzero_in_v1680`: `True`
- `hard_stops_preserved`: `True`

## Safety Scope

This script performed host-only analysis only. It did not contact the device, flash, reboot, send QMI payloads, start service-manager/PM actors, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
