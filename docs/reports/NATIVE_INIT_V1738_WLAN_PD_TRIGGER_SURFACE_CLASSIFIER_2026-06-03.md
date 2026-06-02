# Native Init V1738 WLAN-PD Trigger Surface Classifier

## Summary

- Cycle: `V1738`
- Type: host-only/source-only modem-side WLAN-PD trigger surface classifier
- Decision: `v1738-pd-trigger-is-modem-autoload-missing-pass`
- Result: `PASS`
- Label: `pd-trigger-is-modem-autoload-missing`
- Evidence: `tmp/wifi/v1738-wlan-pd-trigger-surface-classifier`

## Android-good Surface

- `wlfw_start` / `wlfw_service_request`: `8.39641` s / `8.430774` s
- ICNSS QMI / BDF / `wlan0`: `9.445275` s / `9.513055` s / `14.772258` s
- companion services running: rmt_storage `True`, tftp_server `True`, pd_mapper `True`
- restart-PD marker in current Android-good evidence: `False`

## Native V1736 Surface

- `wlfw_start` / `wlfw_service_request` / worker success hits: `1` / `1` / `1`
- WLFW indication-register QMI / capability QMI hits: `0` / `0`
- WLAN-PD listener state / indication: `uninit` / `0`
- WLFW service 69 / requested `wlanmdsp`: `0` / `0`
- tftp running: `1`

## Source Surface

- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss_qmi.c`: `wlfw_new_server` line `1217`, `qmi_add_lookup(WLFW_SERVICE_ID)` line `1275`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c`: driver registration waits on FW-ready line `1275`
- `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/service-notifier.c`: listener registration line `319`, explicit restart-PD API line `648`

## Classification

The available AP-side source surfaces are passive for initial WLAN-PD bring-up: ICNSS registers a WLFW service lookup and reacts to `wlfw_new_server`; service-notifier registers/listens and reports current state; QCACLD registration waits for FW-ready. The only explicit PD mutation surface found in this source set is `service_notif_pd_restart`, but current Android-good evidence does not show a restart-PD marker and that path remains outside the active read-only branch.

V1738 therefore classifies the current blocker as modem-side autoload missing in native: Android reaches WLAN-PD/WLFW with the companion services running, while native reaches the CNSS worker and has tftp running but receives no WLAN-PD UP, no WLFW service 69, and no `wlanmdsp` request.

## Next Gate

- V1739 should be read-only Android-good firmware request capture planning/source-build only first.
- The useful discriminator is whether Android-good `tftp_server` or `rmt_storage` observes a `wlanmdsp.mbn`/modem PD image request before WLAN-PD UP, and which served path is used.
- If Android-good firmware request evidence exists, mirror only that read-only visibility in native before any mutation.
- Do not send restart-PD, do not add PM/service-window actors, do not use `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Checks

- `v1737_basis_passed`: `True`
- `android_good_reaches_wlan_pd_and_wlan0`: `True`
- `android_companion_services_running`: `True`
- `android_no_restart_pd_marker`: `True`
- `native_cnss_worker_reached`: `True`
- `native_stops_before_wlfw_qmi`: `True`
- `native_no_wlan_pd_or_service69_or_wlanmdsp`: `True`
- `icnss_fw_lookup_is_passive`: `True`
- `listener_register_is_state_query`: `True`
- `register_driver_waits_fw_ready`: `True`
- `restart_pd_is_explicit_recovery_api_only`: `True`
- `hard_stops_preserved`: `True`

## Safety Scope

This script performed host-only analysis only. It did not contact the device, flash, reboot, send QMI payloads, start services, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
