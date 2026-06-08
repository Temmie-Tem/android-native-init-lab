# Native Init V2176 Wi-Fi DHCP Stability N3

## Summary

- Decision: `v2176-dhcp-ping-stability-n3-pass`
- Pass: `True`
- Scope: final host runner code after shared transport selector recovery patch.
- Runs: `3`
- Passes: `3`
- Test route: V2176 test boot -> `wifi connect` -> `wifi dhcp` -> one bounded ping -> `wifi cleanup` -> V2174 rollback -> selftest.
- Public report is redacted; raw SSID, PSK, BSSID, MAC, IP, route, DNS, DHCP lease, and ping transcript stay private under run dirs.

## Runs

| Run Dir | Decision | Transport | Connect | DHCP | Ping RC | Cleanup | Rollback Selftest |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| `workspace/private/runs/wifi/v2176-wifi-dhcp-ping-20260608-222301` | `v2176-dhcp-ping-rollback-pass` | `tcpctl` | `wifi-connect-carrier-up` carrier `1` WPA `COMPLETED` | `wifi-dhcp-pass` | `0` | `wifi-cleanup-done` `True` | `True` |
| `workspace/private/runs/wifi/v2176-wifi-dhcp-ping-20260608-222846` | `v2176-dhcp-ping-rollback-pass` | `tcpctl` | `wifi-connect-carrier-up` carrier `1` WPA `COMPLETED` | `wifi-dhcp-pass` | `0` | `wifi-cleanup-done` `True` | `True` |
| `workspace/private/runs/wifi/v2176-wifi-dhcp-ping-20260608-223417` | `v2176-dhcp-ping-rollback-pass` | `tcpctl` | `wifi-connect-carrier-up` carrier `1` WPA `COMPLETED` | `wifi-dhcp-pass` | `0` | `wifi-cleanup-done` `True` | `True` |

## Phase Timers

| Timer | Min Sec | Max Sec | Avg Sec |
| --- | ---: | ---: | ---: |
| `artifact_upload` | 0.000 | 0.000 | 0.000 |
| `connect_window` | 133.230 | 133.690 | 133.518 |
| `dhcp_ping_window` | 3.705 | 3.810 | 3.743 |
| `flash_boot_wait` | 65.046 | 67.382 | 65.850 |
| `preflight_transport` | 0.968 | 0.977 | 0.973 |
| `rollback` | 64.591 | 65.006 | 64.748 |
| `selftest` | 0.221 | 60.937 | 40.672 |

## Tooling Note

- One intermediate no-flash preflight failure occurred before the final N=3 set because the shared selector did not yet apply the serial prompt-noise recovery used by command steps.
- The selector now retries `version`/`status` probes after `hide` on busy/protocol-noise; the final N=3 set was run after that patch.
