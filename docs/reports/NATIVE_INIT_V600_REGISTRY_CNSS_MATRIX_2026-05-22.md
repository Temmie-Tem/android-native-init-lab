# Native Init V600 Registry/CNSS Matrix Report

- date: `2026-05-22 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_registry_cnss_matrix_v600.py`
- evidence: `tmp/wifi/v600-registry-cnss-matrix/`

## Scope

V600 is host-only. It compared Android reference dmesg with V598/V599 native
evidence. It did not contact the device, send QRTR/QMI packets, start daemons,
start service-manager, start Wi-Fi HAL, write `qcwlanstate`, scan, connect, use
credentials, run DHCP, change routes, or ping externally.

## Result

```text
decision: v600-cnss-runtime-and-registry-gap-classified
pass: True
reason: native reaches QRTR TX, modem sysmon, service-notifier 180, and CNSS netlink, but cnss-daemon never reaches wlfw_start and repeats binder -22; registry_missing=sysmon_slpi,sysmon_cdsp,sysmon_adsp,service_notifier_74,sysmon_esoc0; WLFW service 69 readback is empty
next: bounded service-manager/binder dependency proof around CNSS daemon; still no qcwlanstate, Wi-Fi HAL, scan/connect, or external ping
```

## Matrix Summary

Native now matches Android for the lower modem path:

```text
qrtr_rx
qrtr_tx
sysmon_modem
service_notifier_180
cnss_diag_netlink
cnss_daemon_netlink
```

Native still misses the service-registry side channels:

```text
sysmon_slpi
sysmon_cdsp
sysmon_adsp
service_notifier_74
sysmon_esoc0
```

Native also misses the WLFW path:

```text
wlfw_start
wlfw_thread
wlan_pd
qmi_server_connected
bdf_regdb
bdf_bdwlan
wlan_fw_ready
wlan0
```

## CNSS Runtime Gap

The strongest new signal is that native `cnss-daemon` does start far enough to
open CNSS netlink sockets, but does not reach `wlfw_start`.

```text
cnss_daemon_netlink_count=5
cnss_daemon_binder_ioctl_fail_count=1
cnss_daemon_binder_tx_fail_count=21
wlfw_start_count=0
wlfw_thread_count=0
```

Timing:

```text
native sysmon_modem_to_service_notifier_180=721.370ms
native cnss_daemon_netlink_to_binder_fail=50.515ms
android cnss_daemon_start_to_wlfw_start=182.947ms
android wlfw_thread_to_wlan_pd=1097.136ms
```

This changes the next target: the remaining blocker is not just missing QRTR or
CNSS process startup. CNSS starts, but its Android runtime/binder environment is
not sufficient for it to enter WLFW.

## WLFW QRTR Readback

V600 preserved the V598 readback result:

```text
service=69 instance=0 service_events=0 end_of_list=1 timeout=0 qmi_attempted=0
service=69 instance=1 service_events=0 end_of_list=1 timeout=0 qmi_attempted=0
```

So WLFW service `69` is still unpublished in native.

## Interpretation

- `service-notifier 180` is necessary but not sufficient.
- The absence of `service-notifier 74` and sibling `sysmon-qmi` services remains
  useful context, but the most actionable runtime blocker is now
  `cnss-daemon` binder failure before `wlfw_start`.
- Retrying `qcwlanstate`, Wi-Fi HAL, scan/connect, credentials, DHCP, routing,
  or external ping remains premature.

## Next Gate

Recommended V601:

1. Preserve the V598 lower-readiness path:
   firmware mounts, `subsys_modem` holder, QRTR RX gate, and companion order.
2. Add a bounded service-manager/binder dependency proof around `cnss-daemon`.
3. Observe only whether binder failures disappear and `wlfw_start` appears.
4. Keep Wi-Fi HAL, `qcwlanstate`, scan/connect, credentials, DHCP, routing, and
   external ping blocked until WLFW/BDF/`wlan0` readiness appears.
