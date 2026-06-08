# Native Init V2176 Wi-Fi DHCP Ping Live Validation

## Summary

- Decision: `v2176-dhcp-ping-rollback-pass`
- Pass: `True`
- Reason: carrier, DHCP, bounded ping, cleanup, and rollback selftest passed
- Run dir: `workspace/private/runs/wifi/v2176-wifi-dhcp-ping-20260608-223417`
- Test image: `workspace/private/inputs/boot_images/boot_linux_v2176_wifi_dhcp.img`
- Test SHA256: `1defb35d2fbbefba5972046ba2c15391329db10bfc2201bdbd0b787279aa668d`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2174_wifi_urandom_connect.img`
- Rollback SHA256: `cda957e4302d66e407fc97a95932501f0ef2ac655ee264c94519111fece0b3ba`

## Connectivity Scope

- Commands: `wifi connect [profile]`, `wifi dhcp [profile]`, one bounded ping, `wifi cleanup`.
- DHCP may install temporary wlan0 route/DNS. External ping is runner/test scope.
- Raw SSID, PSK, BSSID, MAC, assigned IP, route, DNS, DHCP lease, and ping transcript are not written to this public report.
- Connect decision: `wifi-connect-carrier-up` carrier `1` WPA `COMPLETED`.
- DHCP decision: `wifi-dhcp-pass` rc `0` IPv4 assigned `1` default route `1` nameservers `2`.
- Ping target: `google.com` rc `0` bytes_from `1`.
- Cleanup: `wifi-cleanup-done` ok `True`.
- Secret values logged: connect `0` dhcp `0`.

## Phase Timers

- `preflight_transport`: `0.968` sec
- `flash_boot_wait`: `65.046` sec
- `connect_window`: `133.69` sec
- `dhcp_ping_window`: `3.715` sec
- `rollback`: `65.006` sec
- `selftest`: `0.221` sec
- `artifact_upload`: `0.0` sec

## Rollback

- Rollback OK: `True`
- Rollback attempt: `from-native`
- Rollback selftest fail=0: `True`
