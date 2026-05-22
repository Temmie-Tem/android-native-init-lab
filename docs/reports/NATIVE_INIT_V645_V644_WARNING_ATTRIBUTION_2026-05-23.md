# Native Init V645 V644 Warning Attribution Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_v644_warning_attribution_v645.py`
- evidence: `tmp/wifi/v645-v644-warning-attribution/`
- decision: `v645-service74-window-warning-risk-classified`

## Scope

V645 is host-only. It compares existing V619/V627/V642/V644 manifests and does
not contact the device, mutate sysfs, start daemons, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, or ping externally.

## Result

```text
decision: v645-service74-window-warning-risk-classified
pass: True
reason: clean-DSP alone and service180-only windows are warning-free, while V644 warning follows service74 by 11.789ms; V619 proves warning can also occur without service74 under direct DSP/sibling path
next: plan V646 host-only Android post-service74 timing comparison; do not repeat V644 live or start HAL/qcwlanstate
```

## Comparison

| run | pass | order | children | CNSS | svc180 | svc74 | WLAN-PD | warning | svc74→warning |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| V619 | false | `qrtr_ns,pd_mapper,rmt_storage,tftp_server` | 4 | false | 0 | 0 | 0 | 21 | - |
| V627 | true | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` | 6 | true | 1 | 0 | 0 | 0 | - |
| V642 | true | `qrtr_ns,pd_mapper,rmt_storage,tftp_server` | 4 | false | 0 | 0 | 0 | 0 | - |
| V644 | false | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` | 6 | true | 1 | 1 | 0 | 5 | `11.789 ms` |

## Interpretation

V645 narrows the warning boundary:

- clean-DSP state alone is not enough to trigger the warning: V642 is
  warning-free;
- service `180` with CNSS children is not enough to trigger the warning: V627
  is warning-free;
- V644 publishes service `74` and then hits the warning about `11.789 ms`
  later;
- V619 shows the warning class can also happen without service `74` when the
  direct DSP/sibling path is used.

Therefore the next live action must not be another V644 retry and must not be
HAL/qcwlanstate. The correct next step is to understand Android's post-service
`74` timing and whether Android has an extra ACK/publisher/delay before
WLAN-PD/WLFW that native is missing.

## Next Gate

Proceed to V646 as host-only Android post-service74 timing comparison:

1. locate Android service `74`, WLAN-PD, WLFW/QMI, BDF, and `wlan0` timestamps
   in existing Android evidence;
2. compare V644's service `74` → warning `11.789 ms` path against Android's
   service `74` → WLAN-PD/WLFW path;
3. keep V644 live retry, HAL, `qcwlanstate`, scan/connect, credentials, DHCP,
   route changes, and external ping blocked until the warning boundary is
   understood.
