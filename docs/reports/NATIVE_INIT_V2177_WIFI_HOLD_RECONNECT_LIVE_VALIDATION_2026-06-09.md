# Native Init V2177 Wi-Fi Hold Reconnect Live Validation

## Summary

- Decision: `v2177-hold-reconnect-rollback-pass`
- Pass: `True`
- Reason: V2176 Wi-Fi held through the bounded idle window, reconnected after cleanup, and rolled back cleanly
- Run dir: `workspace/private/runs/wifi/v2177-wifi-hold-reconnect-20260609-003849`
- Test image: `workspace/private/inputs/boot_images/boot_linux_v2176_wifi_dhcp.img`
- Test SHA256: `1defb35d2fbbefba5972046ba2c15391329db10bfc2201bdbd0b787279aa668d`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2174_wifi_urandom_connect.img`
- Rollback SHA256: `cda957e4302d66e407fc97a95932501f0ef2ac655ee264c94519111fece0b3ba`

## Scope

- Commands: `wifi connect`, `wifi dhcp`, bounded hold/idle sampling, one bounded ping, `wifi cleanup`, reconnect, DHCP, one bounded ping, final cleanup.
- Raw SSID, PSK, BSSID, MAC, assigned IP, route, DNS, DHCP lease, and ping transcript are not written to this public report.
- Hold window: `180` sec; samples `6`; sample OK `True`; final ping rc `0`.
- Hold gating values: carrier `['1', '1', '1', '1', '1', '1']` route `['1', '1', '1', '1', '1', '1']` resolv `['1', '1', '1', '1', '1', '1']`.
- Hold observed non-gating values: operstate `['up', 'up', 'up', 'up', 'up', 'up']` supplicant_count `['0', '0', '0', '0', '0', '0']` udhcpc_pidfile `['0', '0', '0', '0', '0', '0']`.
- Initial connect: `wifi-connect-carrier-up` carrier `1` WPA `COMPLETED`.
- Initial DHCP: `wifi-dhcp-pass` ping rc `0`.
- Disconnect cleanup: `wifi-cleanup-done` residue clean `True`.
- Reconnect: `wifi-connect-carrier-up` carrier `1` WPA `COMPLETED`.
- Reconnect DHCP: `wifi-dhcp-pass` ping rc `0`.
- Final cleanup: `wifi-cleanup-done` residue clean `True`.
- Secret values logged: initial connect `0` initial DHCP `0` reconnect connect `0` reconnect DHCP `0`.

## Phase Timers

- `preflight_transport`: `0.941` sec
- `flash_boot_wait`: `67.444` sec
- `initial_connect_window`: `133.509` sec
- `initial_dhcp_ping_window`: `2.878` sec
- `hold_idle_window`: `181.346` sec
- `disconnect_cleanup_window`: `1.035` sec
- `reconnect_window`: `9.381` sec
- `reconnect_dhcp_ping_window`: `2.673` sec
- `final_cleanup_window`: `1.133` sec
- `rollback`: `64.692` sec
- `selftest`: `0.407` sec
- `artifact_upload`: `0.0` sec

## Rollback

- Rollback OK: `True`
- Rollback attempt: `from-native`
- Rollback selftest fail=0: `True`
