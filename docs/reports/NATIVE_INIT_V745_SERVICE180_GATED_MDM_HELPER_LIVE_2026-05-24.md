# Native Init V745 Service180-gated MDM Helper Live Report

- date: `2026-05-24 KST`
- native build on device: `A90 Linux init 0.9.68 (v724)`
- helper version deployed: `a90_android_execns_probe v123`
- helper sha256: `1456974a114240380dce30a855d3571985ae4587ab61366fb3426862ccd59240`
- deploy evidence: `tmp/wifi/v745-execns-helper-v123-deploy-run-serial1850/`
- live evidence: `tmp/wifi/v745-mdm-helper-service180-live-current/`

## Summary

V745 helper v123 was deployed successfully. The bounded live proof then reached
the lower CNSS stack and preserved the safety boundary, but service-notifier
`180` did not appear in that boot window. Because the gate stayed closed,
`mdm_helper` was not started.

## Results

| item | result |
| --- | --- |
| v123 deploy | `execns-helper-v123-deploy-pass` |
| remote helper SHA | `1456974a114240380dce30a855d3571985ae4587ab61366fb3426862ccd59240` |
| live decision | `v745-service180-gate-not-open` |
| `mss` | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` | `OFFLINING -> OFFLINING -> OFFLINING` |
| QRTR RX/TX | present |
| `sysmon-qmi` | present |
| service-notifier `180` | absent |
| MHI/QCA6390/WLFW/BDF/`wlan0` | absent |
| `mdm_helper` | not started |
| service-manager / Wi-Fi HAL / scan / connect / ping | not executed |
| postflight cleanup | reboot cleanup healthy |

## Interpretation

The V745 failure is not a helper deploy failure. It shows service-notifier
`180` is not stable enough to be the next gate. The more reproducible lower
marker in this run is `sysmon-qmi`, so the next bounded proof should gate
`mdm_helper` on `sysmon-qmi` instead of service `180`.

## Follow-up

V746 implements helper v124 with
`wifi-companion-sysmon-gated-mdm-helper-start-only`. It still remains below
service-manager, Wi-Fi HAL, scan/connect, DHCP/routing, credentials, and
external ping.
