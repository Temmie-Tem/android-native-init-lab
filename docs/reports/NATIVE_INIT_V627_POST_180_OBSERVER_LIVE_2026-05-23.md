# Native Init V627 Post-180 Observer Live Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_post_180_observer_v627.py`
- evidence: `tmp/wifi/v627-post-180-observer-live-v2/`
- decision: `v627-post-180-service74-missing`

## Scope

V627 reused the V598/v100 safe native path:

```text
subsys_modem holder -> QRTR RX gate -> lower companion start-only -> WLFW QRTR readback
```

The run did not write DSP boot nodes, open `esoc0`, start service-manager,
start Wi-Fi HAL, scan/connect/link-up, use Wi-Fi credentials, run DHCP, change
routes, or ping externally.

One rejected first attempt exists at
`tmp/wifi/v627-post-180-observer-live/`: the runner set helper
`--timeout-sec=45`, but helper v100 only accepts `<1..30>`. The runner was
fixed to default to `30 s`, and only the second live run is the accepted V627
evidence.

## Result

```text
decision: v627-post-180-service74-missing
pass: True
reason: service-notifier 180 reproduced, but service 74/WLAN-PD/WLFW service 69 remained absent for 31.65s after 180
next: classify lower service 74 publisher dependency before HAL/qcwlanstate/connect
```

## Evidence Matrix

| subject | result | evidence | interpretation |
| --- | --- | --- | --- |
| native health after cleanup | pass | post-reboot `version_seen=True`, `status_healthy=True`; manual `bootstatus` shows `BOOT OK`, `fail=0` | live proof cleaned up safely |
| lower readiness | pass | QRTR RX/TX, modem `sysmon-qmi`, service-notifier `180` all present | V625 partial positive reproduced |
| service-notifier `74` | missing | `service_notifier_74=0` for `31.65 s` after `180` | active blocker remains lower service `74` publication |
| WLAN-PD / WLFW / firmware | missing | `wlan_pd=0`, `qmi_server_connected=0`, `wlfw_start=0`, `wlan_fw_ready=0`, `wlan0=0` | HAL/qcwlanstate/connect remain premature |
| WLFW service `69` readback | clean empty | instances `0/1` both end-of-list, `service_events=0`, `timeouts=0`, `qmi_attempted=0` | absence is publication-side, not readback transport failure |
| CNSS userspace | binder blocked | `cnss_diag` netlink at `+223.853 ms`, `cnss-daemon` netlink at `+418.972 ms`, binder failure at `+468.501 ms` | binder/runtime remains a later issue, not enough to create service `74` |
| safety | clean | `kernel_warning=0`, no Wi-Fi bring-up | continue bounded lower gates |

## Timeline

```text
QRTR RX:             161.890670
QRTR TX:             164.343560
modem sysmon-qmi:    164.344234
service-notifier 180:165.067834
cnss_diag netlink:   165.291687
cnss-daemon netlink: 165.486806
binder failure:      165.536335
service-notifier 74: missing
WLAN-PD:             missing
WLFW service 69:     end-of-list
kernel warning:      0
```

## Interpretation

The V598/v100 path is stable enough to reproduce `service-notifier 180`, but
native still does not publish Android's immediate follow-up service `74`.

This moves the blocker one step lower:

- not Wi-Fi credentials;
- not scan/connect/DHCP;
- not Wi-Fi HAL start;
- not `qcwlanstate` retry;
- not a WLFW readback timeout;
- likely a missing lower publisher/dependency that Android satisfies between
  service `180` and service `74`.

## Next Gate

Proceed to V628 as a host-only classifier first:

1. compare Android V622 and native V627 around the post-`180` service `74`
   publisher path;
2. inspect service-registry/service-locator/QRTR participants visible before
   Android service `74`;
3. keep service-manager, HAL, scan/connect, credentials, DHCP, routes, and
   external ping blocked until service `74`, WLAN-PD, WLFW service `69`, or
   firmware-ready advances.
