# Native Init V1097 PM Server onTransact Tracefs Report

## Summary

V1097 passed. The V1095 provider-positive PM observer window was replayed while
tracefs-only uprobes were armed on `libperipheral_client.so` client and
server-side Binder symbols.

Decision:

```text
v1097-pm-server-ontransact-hit-mdm3-still-offline
```

This closes the hypothesis that `cnss-daemon` issues a PM client request but it
never reaches `pm-service`. It does reach the PM Binder server:
`Binder:<pm-service-pid>_*` threads hit `BnPeripheralManager::onTransact`
after `cnss-daemon` entered `pm_client_register` and `pm_register_connect`.
mdm3 still remained `OFFLINING`, and no WLFW/`wlan0` progress occurred.

## Evidence

| item | path |
| --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_pm_server_ontransact_tracefs_live_v1097.py` |
| predecessor evidence | `tmp/wifi/v1095-pm-cnss-voter-surface-live/manifest.json` |
| live evidence | `tmp/wifi/v1097-pm-server-ontransact-tracefs-live/manifest.json` |
| live summary | `tmp/wifi/v1097-pm-server-ontransact-tracefs-live/summary.md` |
| collector transcript | `tmp/wifi/v1097-pm-server-ontransact-tracefs-live/host/pm-server-ontransact-tracefs-observer.txt` |

## Result

```text
tracefs_result: tracefs-uprobe-pass
total_hit_count: 27
cnss_daemon_hit_count: 2
pm_server_ontransact_hit_count: 14
per_mgr_binder_server_hit_count: 14
per_mgr_pid: 1187
mdm3_state: OFFLINING
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

Tracefs counts:

```json
{
  "pm_client_ack": 1,
  "pm_client_connect": 1,
  "pm_client_register": 2,
  "pm_register_connect": 2,
  "pm_server_ontransact": 14,
  "pm_server_ontransact_thunk": 7
}
```

Per-process hits:

```json
{
  "Binder:1187_1": {
    "pm_server_ontransact": 2,
    "pm_server_ontransact_thunk": 2
  },
  "Binder:1187_2": {
    "pm_server_ontransact": 4,
    "pm_server_ontransact_thunk": 4
  },
  "Binder:1187_3": {
    "pm_server_ontransact": 1,
    "pm_server_ontransact_thunk": 1
  },
  "Binder:1195_1": {
    "pm_client_ack": 1
  },
  "cnss-daemon": {
    "pm_client_register": 1,
    "pm_register_connect": 1
  },
  "pm-proxy": {
    "pm_client_connect": 1,
    "pm_client_register": 1,
    "pm_register_connect": 1
  }
}
```

The trace sequence includes the CNSS-to-server transition:

```text
cnss-daemon-1201  ... pm_client_register
cnss-daemon-1201  ... pm_register_connect
Binder:1187_3-1200 ... pm_server_ontransact_thunk
Binder:1187_3-1200 ... pm_server_ontransact
```

## Interpretation

The active blocker moved below Binder delivery:

```text
PM provider visible
  -> pm-proxy PM client path hit
  -> pm-service Binder onTransact hit
  -> cnss-daemon PM client path hit
  -> pm-service Binder onTransact hit
  -> mdm3 still OFFLINING
  -> WLFW service 69 absent
  -> wlan0 absent
```

The current question is no longer whether the CNSS PM request exists or whether
Binder delivers it. Both are true. The next gate should classify either:

1. PM service vote/QMI decision after `onTransact`.
2. Whether PM service lacks a native runtime input needed to translate the
   request into the lower modem/eSoC action.
3. Whether mdm3/eSoC remains independent of this PeripheralManager Binder path.

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
python3 -m py_compile scripts/revalidation/native_wifi_pm_server_ontransact_tracefs_live_v1097.py
python3 scripts/revalidation/native_wifi_pm_server_ontransact_tracefs_live_v1097.py plan
python3 scripts/revalidation/native_wifi_pm_server_ontransact_tracefs_live_v1097.py \
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
decision: v1097-pm-server-ontransact-hit-mdm3-still-offline
pass: True
selftest: fail=0
```
