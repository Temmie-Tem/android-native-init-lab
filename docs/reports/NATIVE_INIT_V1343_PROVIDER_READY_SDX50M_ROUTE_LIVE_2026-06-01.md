# Native Init V1343 Provider-ready SDX50M Route Live

## Summary

- Cycle: `V1343`
- Type: bounded provider-ready SDX50M route live gate
- Decision: `v1343-sdx50m-route-esoc-powerup-observed`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1343-provider-ready-sdx50m-route-live/manifest.json`
  - `tmp/wifi/v1343-provider-ready-sdx50m-route-live/summary.md`
  - `tmp/wifi/v1221-private-cnss-daemon-sdx50m-live/manifest.json`
- Script: `scripts/revalidation/native_wifi_provider_ready_sdx50m_route_live_v1343.py`

## Execution Scope

- Current command executed device actions: `False`
- Recovered from live evidence: `True`
- Live evidence includes PM actor execution: `True`
- Live evidence includes private CNSS start: `True`

## Key Observations

| field | value |
| --- | --- |
| decision | v1221-sdx50m-per-mgr-esoc0 |
| sdx50m_registered | True |
| per_mgr_esoc0_any | True |
| wlfw_or_wlan_dmesg_seen | False |
| wlan0_up | False |
| wifi_hal_start_executed | False |
| scan_connect_executed | False |
| credential_use_executed | False |
| dhcp_route_executed | False |
| external_ping_executed | False |

## Decision

sdx50m_registered=True per_mgr_esoc0_any=True wlfw_or_wlan_dmesg_seen=False wlan0_up=False

V1343 intentionally stops before Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, or external ping. If the lower route reaches eSoC without
`wlan0`, the next unit remains lower-path classification, not active Wi-Fi
connection.

## Next

compare lower failure against V1222/V1324 response gap before Wi-Fi HAL or scan/connect
