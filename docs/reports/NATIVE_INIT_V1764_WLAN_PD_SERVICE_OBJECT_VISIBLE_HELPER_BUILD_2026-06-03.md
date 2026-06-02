# Native Init V1764 WLAN-PD Service-object-visible Helper Build

## Summary

- Cycle: `V1764`
- Type: source/build-only helper mode
- Decision: `v1764-service-object-visible-helper-build-pass`
- Result: PASS
- Reason: helper v330 adds bounded service-object-visible WLAN-PD mode and static artifact sanity passed
- Evidence: `tmp/wifi/v1764-wlan-pd-service-object-visible-helper-build`
- Helper: `stage3/linux_init/helpers/a90_android_execns_probe_v330`
- Helper SHA256: `b24ba21c0f5d49b319942605eaa183cd233699ca1b6afcad9a99999daf69fc9f`

## New Mode

- Mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`
- Allow flag: `--allow-wlan-pd-service-object-visible-trigger`
- Preserved route: V1736 service-manager WLAN-PD route with `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.
- Added narrow surface: `pm_proxy_helper` plus `pm-service` and `vndservice list` provider query.
- Explicitly excluded: broad `pm-proxy`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, eSoC/RC1, restart-PD, PMIC/GPIO/GDSC writes, PCI rescan, platform bind/unbind, firmware writes, and partition writes.

## Required Output Keys

- `wlan_pd_service_object_visible_trigger.provider_seen`
- `wlan_pd_service_object_visible_trigger.requested_wlanmdsp`
- `wlan_pd_service_object_visible_trigger.wlfw_service69_seen`
- `wlan_pd_service_object_visible_trigger.wlan0_present`
- `wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.*` for null branch, `asInterface`, manager register TX, and success path.
- Safety keys: `no_wifi_hal`, `no_scan_connect`, `no_credentials`, `no_dhcp_routes`, `no_external_ping`, `no_esoc0`, `no_forced_rc1`, `no_per_proxy`.

## Artifact Sanity

- `file`: `/home/temmie/dev/A90_5G_rooting/stage3/linux_init/helpers/a90_android_execns_probe_v330: ELF 64-bit LSB executable, ARM aarch64, version 1 (GNU/Linux), statically linked, BuildID[sha1]=5daa44d5bc36f0b14f26b4655da50490d970e300, for GNU/Linux 3.7.0, stripped`
- Marker seen: `True`
- Dynamic section: `There is no dynamic section in this file.`
- Build rc: `0`

## Source Checks

- `allow_flag_present`: `True`
- `child_per_mgr_present`: `True`
- `child_pm_proxy_helper_present`: `True`
- `conditional_per_proxy_only_for_broad_pm`: `True`
- `config_bool_present`: `True`
- `mode_present`: `True`
- `new_order_excludes_per_proxy`: `True`
- `new_order_present`: `True`
- `no_credentials_key_present`: `True`
- `no_dhcp_routes_key_present`: `True`
- `no_esoc_rc1_keys_present`: `True`
- `no_external_ping_key_present`: `True`
- `no_per_proxy_key_present`: `True`
- `no_restart_pd_literal_absent`: `True`
- `no_scan_connect_key_present`: `True`
- `no_wifi_hal_key_present`: `True`
- `provider_query_present`: `True`
- `provider_seen_key_present`: `True`
- `requested_wlanmdsp_key_present`: `True`
- `summary_function_present`: `True`
- `version_v330`: `True`
- `wlan0_key_present`: `True`
- `wlfw_service69_key_present`: `True`

## Classification

- Failed checks: `[]`
- Live/deploy remains a separate gate. This unit only creates the bounded helper artifact needed for the next rollbackable discriminator.
