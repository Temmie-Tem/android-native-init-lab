# Native Init V2282 V2254 Wi-Fi Hold Reconnect Runner

## Summary

- Cycle: `V2282`
- Type: T2 WLAN native-init current-baseline hold/reconnect runner.
- Decision: `v2282-v2254-hold-reconnect-rollback-pass`
- Result: `PASS`
- Reason: V2254 Wi-Fi held through the bounded idle window, reconnected after cleanup, and rolled back cleanly
- Execute mode: `True`
- Evidence: `workspace/private/runs/wifi/v2282-v2254-wifi-hold-reconnect-live-20260612-190726`
- T1 drop trigger: V2280 exhausted the workqueue execute-start oracle for the firmware_class/qcacld-HDD target and no new independent T1 oracle is encoded.

## Images

- Test image: `workspace/private/inputs/boot_images/boot_linux_v2254_wifi_detail_surface.img`
- Test SHA256: `c668e9cd9a3621c955fa369c5d106271a96a949dcaec3774a5719d24b8ba19e9`
- Test version: `A90 Linux init 0.9.272 (v2254-wifi-detail-surface)`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
- Rollback SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Rollback version: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`
- Emergency fallback image present: `True` SHA match `True`

## Credential Gate

- Presence only: `{'profile': 'default', 'ssid_present': True, 'psk_present': True, 'valid': True, 'secret_values_logged': 0}`
- Env sources: `[{'path': 'workspace/private/secrets/a90-wifi-test.env', 'present': False, 'loaded_keys': []}, {'path': 'tmp/wifi/.wifi-test.env', 'present': True, 'loaded_keys': ['A90_WIFI_SSID', 'A90_WIFI_PSK']}]`
- Raw SSID, PSK, BSSID, MAC, assigned IP, route, DNS, DHCP lease, and ping transcript are not written to this public report.

## Live Evidence

- Current preflight selftest fail=0: `True`
- V2254 flash OK: `True`
- V2254 health: `{'selftest_ok': True, 'status_ok': True, 'version_ok': True}`
- Initial connect: `wifi-connect-carrier-up` carrier `1` WPA `COMPLETED`.
- Initial DHCP: `wifi-dhcp-pass` ping rc `0`.
- Hold window: `180` sec; samples `6`; sample OK `True`; final ping rc `0`.
- Hold gating values: carrier `['1', '1', '1', '1', '1', '1']` route `['1', '1', '1', '1', '1', '1']` resolv `['1', '1', '1', '1', '1', '1']`.
- Disconnect cleanup: `wifi-cleanup-done` residue clean `True`.
- Reconnect: `wifi-connect-carrier-up` carrier `1` WPA `COMPLETED`.
- Reconnect DHCP: `wifi-dhcp-pass` ping rc `0`.
- Final cleanup: `wifi-cleanup-done` residue clean `True`.
- Rollback OK: `True` via `from-native` selftest fail=0 `True`.

## Phase Timers

- `host_preflight`: `0.124` sec
- `transport_preflight`: `1.56` sec
- `current_selftest_preflight`: `0.408` sec
- `flash_v2254`: `53.584` sec
- `test_boot_health`: `0.772` sec
- `initial_connect_window`: `132.751` sec
- `initial_dhcp_ping_window`: `2.886` sec
- `hold_idle_window`: `181.343` sec
- `disconnect_cleanup_window`: `1.034` sec
- `reconnect_window`: `9.419` sec
- `reconnect_dhcp_ping_window`: `2.781` sec
- `final_cleanup_window`: `1.037` sec
- `rollback`: `127.208` sec

## Safety Scope

- Live mode is disabled unless `--execute` and the exact confirmation token are supplied.
- Live mode exits before flash if Wi-Fi credentials are absent or invalid.
- Flash path is limited to boot partition via `native_init_flash.py`.
- Wi-Fi actions are explicitly scoped to connect, DHCP, bounded ping, hold/idle sampling, cleanup, reconnect, DHCP, bounded ping, and final cleanup.
- No Wi-Fi scan is run by this runner.
- No credentials, SSID, BSSID, MAC, IP, route, DHCP lease, DNS server, or ping transcript is committed.
- No BPF attach, tracefs write, `probe_write_user`, eSoC/PCIe/GDSC/PMIC/GPIO, platform bind/unbind, or `sda29` write.
