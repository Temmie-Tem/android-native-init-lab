# Native Init V602 Service-Manager Ordering Gap Report

- date: `2026-05-22 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_service_manager_ordering_gap_v602.py`
- evidence: `tmp/wifi/v602-service-manager-ordering-gap/`

## Scope

V602 is host-only. It compared Android reference evidence with V598 and V601.
It did not contact the device, start daemons, start service-manager, send
QRTR/QMI payloads, start Wi-Fi HAL, write `qcwlanstate`, scan, connect, use
credentials, run DHCP, change routes, or ping externally.

## Result

```text
decision: v602-service-manager-ordering-gap-classified
pass: True
reason: V598 proves QRTR TX/sysmon/service-notifier 180 without service-manager, while V601 proves service-manager clears binder transaction failures but loses service-notifier 180 and still has empty WLFW readback
next: implement a bounded qrtr-first/delayed service-manager companion proof before any qcwlanstate, Wi-Fi HAL, scan/connect, or external ping
```

## Marker Comparison

Android reference:

```text
service_notifier_180=1
service_notifier_74=1
wlan_pd=2
wlfw_start=1
qmi_server_connected=1
bdf_regdb=1
bdf_bdwlan=1
wlan_fw_ready=1
wlan0=21
```

V598:

```text
qrtr_rx=1
qrtr_tx=1
sysmon_modem=1
service_notifier_180=1
cnss_diag_netlink=1
cnss_daemon_netlink=5
binder_transaction_failed=21
perfd_client_failed=1
WLFW_readback_service_events=0
```

V601:

```text
qrtr_rx=1
qrtr_tx=1
sysmon_modem=1
service_notifier_180=0
cnss_diag_netlink=1
cnss_daemon_netlink=5
binder_transaction_failed=0
binder_ioctl_unsupported=2
perfd_client_failed=1
WLFW_readback_service_events=0
```

## Timing

```text
android sysmon_modem_to_service_notifier_180=22.262ms
v598 sysmon_modem_to_service_notifier_180=721.370ms
v601 sysmon_modem_to_service_notifier_180=missing
```

## Interpretation

V601 is not a strict superset of V598. It fixes one blocker but regresses another
observable readiness marker:

- V598 has the lower modem registry path through service-notifier `180`.
- V601 has the service-manager/binder runtime and clears binder transaction
  failures.
- Neither path reaches service-notifier `74`, WLAN-PD, WLFW, BDF, FW-ready, or
  `wlan0`.

Therefore, retrying `qcwlanstate`, Wi-Fi HAL, scan/connect, credentials, DHCP,
routing, or external ping remains premature.

## Next Gate

Recommended V603:

1. Add or use a bounded companion mode that starts QRTR/modem companion services
   first, then starts service-manager after the lower QRTR/sysmon path has time
   to publish service-notifier `180`.
2. Keep `subsys_modem` holder and reboot cleanup.
3. Require both conditions before advancing:
   - service-notifier `180` remains present;
   - binder transaction failures remain cleared.
4. Continue to block `qcwlanstate`, Wi-Fi HAL, scan/connect, credentials, DHCP,
   routing, and external ping until WLFW service `69`, BDF, FW-ready, or `wlan0`
   appears.
