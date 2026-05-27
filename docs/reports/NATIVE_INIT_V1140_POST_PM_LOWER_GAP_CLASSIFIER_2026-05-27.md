# Native Init V1140 Post-PM Lower Gap Classifier Report

Date: `2026-05-27`

## Result

- Decision: `v1140-post-pm-esoc0-only-gap-classified`
- Pass: `true`
- Runner: `scripts/revalidation/native_wifi_post_pm_lower_gap_classifier_v1140.py`
- Manifest: `tmp/wifi/v1140-post-pm-lower-gap-classifier/manifest.json`
- Summary: `tmp/wifi/v1140-post-pm-lower-gap-classifier/summary.md`

## Summary

V1140 is host-only. It consumes the V1139 live manifest and does not contact the
device.

The V1071 `pm-service exit 255`/BPF-uProbe direction is now obsolete for the
current tree: V1139 shows the PM provider path is alive, `per_mgr` exits cleanly,
`per_mgr` and `pm_proxy_helper` both reach `/dev/subsys_modem`, and CNSS PM
`register`/`connect` both return `0x0`.

The remaining blocker is lower than PM provider/CNSS:

```text
PM provider + CNSS register/connect OK
  -> mdm_helper reaches /dev/esoc-0
  -> no /dev/subsys_esoc0 fd
  -> no MHI pipe
  -> no ks
  -> no WLFW service 69 / BDF / wlan0
  -> mdm3 remains OFFLINING
```

## Evidence

| item | value |
| --- | --- |
| V1139 manifest | `tmp/wifi/v1139-post-pm-mdm-helper-esoc-live-r2/manifest.json` |
| V1139 decision | `v1139-post-pm-mdm-helper-lower-artifact-observed` |
| V1139 pass | `true` |
| `pm_client_register_ret` | `0x0` |
| `pm_client_connect_ret` | `0x0` |
| `per_mgr` exit | `0` |
| `per_mgr_subsys_modem_seen` | `1` |
| `pm_proxy_helper_subsys_modem_seen` | `1` |
| `mdm_helper` `/dev/esoc-0` count | `1` |
| `mdm_helper` `/dev/subsys_esoc0` count | `0` |
| MHI pipe count | `0` |
| `ks` count | `0` |
| QRTR services `69/74/180` | `0/0/0` |
| `mdm3` after observer | `OFFLINING` |

## Interpretation

The next work should not return to `pm-service` early-exit tracing and should not
start Wi-Fi HAL or scan/connect yet. The highest-value next gate is a bounded
post-PM `mdm_helper` lower-trace support path that captures:

- `mdm_helper` syscall/ioctl/wchan/status/fd progression after `/dev/esoc-0`
- whether it enters an ESOC wait/request path or stalls in userspace
- Android `ks`/MHI contract deltas that are still absent in native init

The gate must remain observational unless a later plan explicitly proves a safe
trigger. Do not issue a blind `/dev/subsys_esoc0` trigger from this classifier.

## Safety

- Device commands executed: `false`
- Device mutations: `false`
- Tracefs writes: `false`
- Wi-Fi HAL start: `false`
- Scan/connect/link-up: `false`
- Credential use: `false`
- DHCP/route: `false`
- External ping: `false`
- Boot image/partition write/flash: not executed
