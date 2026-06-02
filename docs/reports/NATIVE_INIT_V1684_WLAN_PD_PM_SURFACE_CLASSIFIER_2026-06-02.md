# Native Init V1684 WLAN-PD PM Surface Classifier

## Summary

- Cycle: `V1684`
- Type: host-only classifier
- Decision: `v1684-select-wlan-pd-pm-trio-source-build`
- Result: PASS
- Reason: V1683 preserved the internal-modem firmware-serve route and started cnss-daemon, but still lacked wlfw_start; Android-good has pm_proxy_helper, per_mgr, and per_proxy before cnss-daemon, and V1683 did not start that PM trio.
- Next: Build the next rollbackable test-boot source unit with the V1683 internal-modem route plus pm_proxy_helper/per_mgr/per_proxy before cnss-daemon, while keeping mdm_helper, /dev/subsys_esoc0, forced RC1, Wi-Fi HAL, wificond, scan/connect, credentials, DHCP/routes, and external ping disabled.
- Evidence: `tmp/wifi/v1684-wlan-pd-pm-surface-classifier`

## Android-good PM Surface

| service | boottime_s | before cnss-daemon |
| --- | --- | --- |
| pm_proxy_helper | 5.813594475 | True |
| per_mgr | 6.987724683 | True |
| per_proxy | 7.848075047 | True |

## Native V1683 Surface

| signal | value |
| --- | --- |
| label | service-window-still-no-wlfw |
| legacy firmware-serve label | firmware-not-requested |
| subsys_modem holder opened | True |
| tftp running | True |
| cnss-daemon started | True |
| wlfw_start seen | False |
| wlfw_service_request seen | False |
| WLFW service 69 seen | False |
| requested wlanmdsp | False |
| pm_proxy_helper started | False |
| per_mgr started | False |
| per_proxy started | False |
| mdm_helper started | False |
| Wi-Fi HAL started | False |
| wificond started | False |
| eSoC/forced RC1 marker | False |
| property requests | hwservicemanager.ready |

## Checks

| check | value |
| --- | --- |
| v1681_positive_android_wlfw_chain | True |
| android_pm_trio_before_cnss | True |
| v1683_valid_single_label | True |
| v1683_internal_modem_route_intact | True |
| v1683_cnss_started_no_wlfw | True |
| v1683_pm_trio_absent | True |
| v1683_no_esoc_or_rc1 | True |
| v1683_no_hal_wificond_mdm_helper | True |

## Interpretation

- V1683 closed the service-manager-only experiment: service managers plus the internal-modem holder were not sufficient for `cnss-daemon wlfw_start`.
- Android-good starts `pm_proxy_helper`, `per_mgr`, and `per_proxy` before `cnss-daemon`; V1683 did not start any of them.
- The next aligned source/build unit is therefore PM-trio-only augmentation of the V1683 route, not MSA/BDF, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or the stopped eSoC/RC1 track.

## Next Gate Contract

- Source/build-only first.
- Preserve the V1683 internal-modem WLAN-PD firmware-serve route and `/dev/subsys_modem` holder.
- Add `pm_proxy_helper`, `per_mgr`, and `per_proxy` before `cnss-daemon`; classify whether this reaches `wlfw_start` or only changes PM lifecycle evidence.
- Keep `mdm_helper`, `/dev/subsys_esoc0`, raw eSoC ioctls, forced RC1, fake-ONLINE, Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP/routes, and external ping disabled.
- Stop after one live label if the source/build unit is later approved/run.

## Inputs

- V1681: `tmp/wifi/v1681-wlan-pd-wlfw-trigger-delta-classifier/manifest.json`
- V1683: `tmp/wifi/v1683-wlan-pd-service-window-handoff`

## Safety

- Host-only classifier. No device command, daemon start, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, boot image write, firmware write, or partition write occurred.
