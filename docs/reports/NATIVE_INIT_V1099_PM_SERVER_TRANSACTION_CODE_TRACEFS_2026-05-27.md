# Native Init V1099 PM Server Transaction Code Tracefs Report

## Summary

V1099 passed. The V1095 provider-positive PM observer window was replayed while
tracefs-only uprobes were armed on `libperipheral_client.so` PM client calls and
PM server `onTransact` dispatch points.

Decision:

```text
v1099-pm-server-transaction-codes-captured-mdm3-still-offline
```

V1099 shows that `pm-proxy` reaches PM server transaction codes `0x1`, `0x3`,
and `0x5`, but `cnss-daemon` only reaches code `0x1` after
`pm_client_register`/`pm_register_connect`. This explains why V1098 saw
`pm-service` Binder activity without QMI send/handle activity: the CNSS path is
still at the register/listener boundary, not the actionable connect/vote path.

## Evidence

| item | path |
| --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_pm_server_transaction_code_tracefs_live_v1099.py` |
| predecessor evidence | `tmp/wifi/v1095-pm-cnss-voter-surface-live/manifest.json` |
| live evidence | `tmp/wifi/v1099-pm-server-transaction-code-tracefs-live/manifest.json` |
| live summary | `tmp/wifi/v1099-pm-server-transaction-code-tracefs-live/summary.md` |
| collector transcript | `tmp/wifi/v1099-pm-server-transaction-code-tracefs-live/host/pm-server-transaction-code-tracefs-observer.txt` |

## Result

```text
tracefs_result: tracefs-uprobe-pass
hit_count: 28
cnss_daemon_hit_count: 2
pm_server_ontransact_hit_count: 21
per_mgr_binder_server_hit_count: 14
per_mgr_pid: 1480
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

Transaction code counts:

```json
{
  "0x1": 4,
  "0x3": 2,
  "0x5": 2,
  "0x5f4e5446": 6
}
```

Transaction codes by Binder thread:

```json
{
  "Binder:1480_1": {
    "0x5f4e5446": 4
  },
  "Binder:1480_2": {
    "0x1": 2,
    "0x3": 2,
    "0x5": 2,
    "0x5f4e5446": 2
  },
  "Binder:1480_3": {
    "0x1": 2
  }
}
```

Observed sequence:

```text
pm-proxy -> pm_client_register -> pm_register_connect -> code 0x1
pm-proxy -> pm_client_connect -> code 0x3
pm-proxy Binder thread -> pm_client_ack -> code 0x5
cnss-daemon -> pm_client_register -> pm_register_connect -> code 0x1
```

The `0x5f4e5446` transactions are Binder interface descriptor probes, not lower
PM action.

## Interpretation

The active blocker is no longer PM client path absence, Binder delivery absence,
or `pm-service` process startup. The remaining gap is that `cnss-daemon` does
not issue the same actionable PM transaction sequence that `pm-proxy` issues:

```text
PM provider visible
  -> pm-proxy PM client path hit
  -> pm-service transaction 0x1/0x3/0x5 hit
  -> cnss-daemon PM client path hit
  -> pm-service transaction 0x1 only
  -> no PM QMI send/handle
  -> mdm3 still OFFLINING
  -> WLFW service 69 absent
  -> wlan0 absent
```

The next gate should map transaction codes to PM method names and classify why
`cnss-daemon` stops after register/listener setup instead of issuing the
connect/vote path that could drive lower modem/eSoC action.

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
python3 -m py_compile scripts/revalidation/native_wifi_pm_server_transaction_code_tracefs_live_v1099.py
python3 scripts/revalidation/native_wifi_pm_server_transaction_code_tracefs_live_v1099.py plan
python3 scripts/revalidation/native_wifi_pm_server_transaction_code_tracefs_live_v1099.py \
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
decision: v1099-pm-server-transaction-codes-captured-mdm3-still-offline
pass: True
selftest: fail=0
```
