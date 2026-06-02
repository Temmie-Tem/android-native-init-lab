# Native Init V1681 WLAN-PD WLFW Trigger Delta Classifier

## Summary

- Cycle: `V1681`
- Type: host-only classifier
- Decision: `v1681-cnss-wlfw-start-trigger-surface-selected`
- Result: PASS
- Reason: V1680 validly triggers the internal modem and tftp companion path, but Android-good emits cnss-daemon wlfw_start/wlfw_service_request before WLAN-PD/QMI/BDF while V1680's live cnss-daemon never emits those markers.
- Next: Next work is a source/build-only no-eSoC WLFW-start trigger-surface gate: preserve the V1680 internal-modem firmware-serve route, add bounded Android pre-CNSS service/provider surface only as needed, and classify cnss-daemon wlfw_start before any firmware/MSA/BDF/scan/connect work.
- Evidence: `tmp/wifi/v1681-wlan-pd-wlfw-trigger-delta-classifier`

## Native V1680

| signal | value |
| --- | --- |
| label | firmware-not-requested |
| tftp_running | True |
| subsys_modem_holder_opened | True |
| mss_loading_seen | True |
| mss_reset_seen | True |
| rmt_storage_efs_seen | True |
| requested_wlanmdsp | False |
| requested_modem | False |
| native_wlfw_start_seen | False |
| native_wlfw_service_request_seen | False |
| wlfw_service69_seen | False |
| cnss_daemon_started | True |
| cnss_daemon_alive_polling | True |
| service_surface_absent | True |
| wifi_hal_absent | True |
| wificond_absent | True |
| per_mgr_absent | True |
| per_proxy_absent | True |

## Android-good WLFW Chain

| marker | count | first_s |
| --- | --- | --- |
| cnss_wlfw_start | 1 | 8.354789 |
| cnss_wlfw_service_request | 1 | 8.387879 |
| wlan_pd | 2 | 9.423396 |
| qmi_server_connected | 1 | 9.425819 |
| bdf_regdb | 1 | 9.487968 |
| wlan_fw_ready | 2 | 14.60932 |
| wlan0 | 6 | 14.774208 |

## Android Pre-CNSS Service Order

| property | seconds | classification |
| --- | --- | --- |
| ro.boottime.vendor.per_proxy_helper | 5.813594 | before cnss-daemon |
| ro.boottime.vendor.qrtr-ns | 6.942195 | before cnss-daemon |
| ro.boottime.vendor.pd_mapper | 6.978435 | before cnss-daemon |
| ro.boottime.vendor.per_mgr | 6.987725 | before cnss-daemon |
| ro.boottime.vendor.rmt_storage | 7.061588 | before cnss-daemon |
| ro.boottime.vendor.tftp_server | 7.064970 | before cnss-daemon |
| ro.boottime.vendor.per_proxy | 7.848075 | before cnss-daemon |
| ro.boottime.cnss_diag | 7.975236 | before cnss-daemon |
| ro.boottime.vendor.mdm_helper | 8.218118 |  |
| ro.boottime.cnss-daemon | 8.222635 |  |

## Checks

| check | value |
| --- | --- |
| v1680_valid_internal_modem_trigger | True |
| native_no_request_no_wlfw | True |
| android_positive_wlfw_chain | True |
| android_wlfw_upstream_of_wlan_pd | True |
| native_cnss_alive_but_wlfw_trigger_absent | True |
| v1680_omitted_android_trigger_surface | True |
| android_pre_cnss_order_available | True |

## Interpretation

- V1680 is now a valid internal-modem trigger: mss loads, comes out of reset, and `rmt_storage` handles modem EFS.
- The missing request is upstream of tftp serving: no `wlanmdsp.mbn` request appears because native never reaches `cnss-daemon wlfw_start` / `wlfw_service_request`.
- Android-good evidence places `cnss-daemon wlfw_start` before WLAN-PD indication, ICNSS QMI, BDF, FW-ready, and `wlan0`.
- Therefore the next blocker is the pre-WLFW `cnss-daemon` trigger surface, not MSA, BDF, firmware-file mutation, tftp timing, or the stopped eSoC/RC1/MDM2AP track.

## Next Gate Contract

- Start source/build-only first.
- Preserve the V1680 internal modem route and companion firmware-serve observation.
- Add only the minimum Android pre-CNSS service/provider surface needed to classify `cnss-daemon wlfw_start`.
- Keep `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, scan/connect, credentials, DHCP/routes, and external ping disabled.
- Do not investigate MSA/BDF or run Wi-Fi connectivity until WLFW service 69 or `wlfw_start` appears.

## Inputs

- V1680: `tmp/wifi/v1680-wlan-pd-firmware-serve-modem-holder-handoff`
- V1331: `tmp/wifi/v1331-android-sdx50m-timing-handoff/v1331-android-sdx50m-timing-recapture-run/manifest.json`
- V661: `tmp/wifi/v661-binder-registration-context-classifier/manifest.json`

## Safety

- Host-only classifier. No device command, live mutation, daemon start, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, boot image write, firmware write, or partition write occurred.
