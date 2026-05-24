# Native Init V791 Current Warning Route Classifier Report

## Result

- decision: `v791-known-asoc-warning-wlfw-route-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_current_warning_route_classifier_v791.py`
- evidence: `tmp/wifi/v791-current-warning-route-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_current_warning_route_classifier_v791.py
python3 scripts/revalidation/native_wifi_current_warning_route_classifier_v791.py plan
python3 scripts/revalidation/native_wifi_current_warning_route_classifier_v791.py run
```

## Evidence Summary

| Signal | V790 | V788 | Notes |
| --- | ---: | ---: | --- |
| CNSS children | `0` | `1` | V790 reproduced the boundary without `cnss_diag`/`cnss-daemon` |
| service-notifier markers | `2` | `2` | service `180` and `74` both present in dmesg |
| `sysmon-qmi` | `4` | `4` | modem plus ADSP/CDSP/SLPI SSCTL |
| ASoC probe count | `2` | `2` | duplicate probe path present |
| `pm_qos` duplicate warning | `1` | `1` | exact ASoC warning signature |
| service `74` -> `pm_qos` | `4.742 ms` | `4.702 ms` | same immediate warning timing class |
| sound card after warning | `506.157 ms` | `513.421 ms` | warning does not stop sound-card registration |
| WLFW/BDF/`wlan0` | `0 / 0 / 0` | `0 / 0 / 0` | actual Wi-Fi continuation still absent |

## Classification

V790 proves the current warning does not require CNSS userspace: lower-only
`qrtr-ns`, `rmt_storage`, `tftp_server`, and `pd-mapper` are enough to reach
service `180/74`, trigger ASoC/APR, and reproduce the duplicate `pm_qos`
warning.

That warning should no longer be treated as the first Wi-Fi blocker by itself.
V649/V650 Android evidence shows the same warning class can occur and still
continue through WLFW, WLAN-PD, BDF, firmware-ready, and `wlan0`. V790 also
continues to sound-card registration after the warning. The current first
useful Wi-Fi blocker remains the post-warning WLFW/service `69` continuation
gap, not the exact ASoC warning signature.

## Safety

- V791 was host-only.
- No device command, reboot, mount, daemon start, Wi-Fi action, credential use,
  network change, boot image write, partition write, or custom kernel flash.
- Evidence reads were bounded to avoid broad scans.

## Next

Plan V792 as a known-ASoC-warning-tolerant CNSS/WLFW readback gate:

1. allow only the exact known ASoC `pm_qos` warning signature;
2. keep all other warning/reference/esoc classes as blockers;
3. keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping
   blocked;
4. define success as WLFW/service `69`, BDF, `wlan0`, or a sharper CNSS
   continuation blocker.
