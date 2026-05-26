# Native Init V1098 PM Service QMI Tracefs Report

## Summary

V1098 passed. The V1095 provider-positive PM observer window was replayed while
tracefs-only uprobes were armed on `/mnt/vendor/bin/pm-service` PLT entries.

Decision:

```text
v1098-pm-service-qmi-loop-active-no-send
```

V1097 proved that the CNSS PM request reaches the `pm-service` Binder server.
V1098 shows that `pm-service` initializes the QMI service loop but does not hit
`qmi_csi_send_ind`, `qmi_csi_send_resp`, or `qmi_csi_handle_event` during the
bounded CNSS request window. mdm3 still remained `OFFLINING`, and no
WLFW/`wlan0` progress occurred.

## Evidence

| item | path |
| --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_pm_service_qmi_tracefs_live_v1098.py` |
| predecessor evidence | `tmp/wifi/v1095-pm-cnss-voter-surface-live/manifest.json` |
| live evidence | `tmp/wifi/v1098-pm-service-qmi-tracefs-live/manifest.json` |
| live summary | `tmp/wifi/v1098-pm-service-qmi-tracefs-live/summary.md` |
| collector transcript | `tmp/wifi/v1098-pm-service-qmi-tracefs-live/host/pm-service-qmi-tracefs-observer.txt` |

## Result

```text
tracefs_result: tracefs-uprobe-pass
hit_count: 33
pm_service_qmi_hit_count: 3
pm_service_qmi_send_hit_count: 0
per_mgr_qmi_hit_count: 3
per_mgr_pid: 1326
mdm3_state: OFFLINING
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

Tracefs counts:

```json
{
  "pm_get_system_info": 1,
  "pm_log_print": 25,
  "pm_property_set": 4,
  "pm_qmi_handle_event": 0,
  "pm_qmi_register": 1,
  "pm_qmi_select": 1,
  "pm_qmi_send_ind": 0,
  "pm_qmi_send_resp": 0,
  "pm_qmi_unregister": 1
}
```

QMI hits:

```json
{
  "pm-service": {
    "pm_qmi_register": 1,
    "pm_qmi_select": 1,
    "pm_qmi_unregister": 1
  }
}
```

The trace sequence shows startup-only QMI loop activity:

```text
pm-service-1329 ... pm_qmi_register
pm-service-1329 ... pm_qmi_select
Binder:1326_2 ... pm_log_print
pm-service-1329 ... pm_qmi_unregister
```

No QMI send or event handling was observed:

```text
pm_qmi_handle_event=0
pm_qmi_send_ind=0
pm_qmi_send_resp=0
```

## Interpretation

The active blocker moved below PM Binder server delivery but above lower QMI
message exchange:

```text
PM provider visible
  -> pm-proxy PM client path hit
  -> pm-service Binder onTransact hit
  -> cnss-daemon PM client path hit
  -> pm-service Binder onTransact hit
  -> pm-service QMI loop registers/selects
  -> no QMI handle/send during CNSS request window
  -> mdm3 still OFFLINING
  -> WLFW service 69 absent
  -> wlan0 absent
```

The next gate should classify why the PM Binder transaction produces log/property
activity but no QMI send/handle path. Likely next questions:

1. Which `BnPeripheralManager::onTransact` case is being executed for the CNSS
   request.
2. Whether the client request is only registration/listener setup rather than a
   vote/connect request that should move mdm3.
3. Whether an Android runtime input is missing before `pm-service` considers the
   request actionable.

## Safety

- No Wi-Fi HAL, scan/connect/link-up, DHCP, route, credential use, or external
  ping executed.
- No `mdm_helper` executed.
- No eSoC open/ioctl, GPIO write, partition write, flash, or reboot executed.
- Tracefs events were removed cleanly; no register/enable/cleanup failure
  remained in the passing run.
- Device remained healthy: post-run `selftest` reported `fail=0`; `netservice`
  stayed USB-local.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_service_qmi_tracefs_live_v1098.py
python3 scripts/revalidation/native_wifi_pm_service_qmi_tracefs_live_v1098.py plan
python3 scripts/revalidation/native_wifi_pm_service_qmi_tracefs_live_v1098.py \
  --allow-tracefs-mount \
  --allow-tracefs-write \
  --allow-vendor-mount \
  --allow-selinuxfs-mount \
  --allow-pm-service-trigger-observer \
  --allow-cnss-daemon-start \
  --assume-yes \
  run
python3 scripts/revalidation/a90ctl.py selftest
python3 scripts/revalidation/a90ctl.py netservice status
```

Result:

```text
decision: v1098-pm-service-qmi-loop-active-no-send
pass: True
selftest: fail=0
```
