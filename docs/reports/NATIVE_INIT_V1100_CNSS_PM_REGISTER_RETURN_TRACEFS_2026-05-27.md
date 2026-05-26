# Native Init V1100 CNSS PM Register Return Tracefs Report

## Summary

V1100 passed. The V1095 provider-positive PM observer window was replayed while
tracefs-only entry and return uprobes were armed on
`libperipheral_client.so`.

Decision:

```text
v1100-cnss-pm-register-blocks-after-code1-mdm3-still-offline
```

`pm-proxy` remains the positive control: it registers with PM, returns `0x0`,
connects, returns `0x0`, and reaches PM server transaction `0x3`. In the same
window, `cnss-daemon` enters `pm_client_register` with
`peripheral="modem"`/`client="cnss-daemon"` and reaches PM server transaction
`0x1`, but `pm_client_register` never returns before the bounded cleanup. It
therefore never calls `pm_client_connect`, so no actionable PM connect/vote path
is issued for CNSS.

## Evidence

| item | path |
| --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_pm_cnss_register_return_tracefs_live_v1100.py` |
| predecessor evidence | `tmp/wifi/v1095-pm-cnss-voter-surface-live/manifest.json` |
| live evidence | `tmp/wifi/v1100-pm-cnss-register-return-tracefs-live/manifest.json` |
| live summary | `tmp/wifi/v1100-pm-cnss-register-return-tracefs-live/summary.md` |
| collector transcript | `tmp/wifi/v1100-pm-cnss-register-return-tracefs-live/host/pm-server-pm-cnss-register-return-tracefs-observer.txt` |

## Result

```text
tracefs_result: tracefs-uprobe-pass
hit_count: 29
cnss_daemon_hit_count: 2
pm_server_ontransact_hit_count: 14
per_mgr_binder_server_hit_count: 14
per_mgr_pid: 1781
mdm3_state: OFFLINING
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

Tracefs counts:

```json
{
  "pm_client_ack_entry": 1,
  "pm_client_connect_entry": 1,
  "pm_client_connect_ret": 1,
  "pm_client_register_entry": 2,
  "pm_client_register_ret": 1,
  "pm_register_connect_entry": 2,
  "pm_server_ontransact": 14,
  "pm_server_ontransact_thunk": 7
}
```

Return values:

```json
{
  "pm-proxy": {
    "pm_client_connect_ret": [
      "0x0"
    ],
    "pm_client_register_ret": [
      "0x0"
    ]
  }
}
```

Register arguments:

```json
{
  "cnss-daemon": [
    {
      "client": "cnss-daemon",
      "peripheral": "modem"
    }
  ],
  "pm-proxy": [
    {
      "client": "PM-PROXY-THREAD",
      "peripheral": "modem"
    }
  ]
}
```

Transaction code mapping used by V1099/V1100:

```json
{
  "0x1": "register",
  "0x2": "unregister",
  "0x3": "connect",
  "0x4": "disconnect",
  "0x5": "event_acknowledge",
  "0x5f4e5446": "interface_transaction",
  "0x6": "show_peripherals"
}
```

## Interpretation

The PM chain is now narrowed to the server-side `register` transaction for the
CNSS client:

```text
PM provider visible
  -> pm-proxy register returns 0
  -> pm-proxy connect returns 0
  -> cnss-daemon register enters
  -> PM server transaction 0x1/register hit
  -> cnss-daemon register does not return
  -> cnss-daemon never calls transaction 0x3/connect
  -> no PM QMI send/handle
  -> mdm3 still OFFLINING
  -> WLFW service 69 absent
  -> wlan0 absent
```

The next gate should classify why PM server code `0x1` does not return for the
CNSS client while it does return for `pm-proxy`. The likely targets are server
reply fields, callback registration behavior, and PM event readiness associated
with `peripheral="modem"` and `client="cnss-daemon"`.

Note: the original V1100 wrapper/report text labeled the two PM client strings
in reverse. V1101 corrected the semantics from disassembly and positive-control
trace comparison.

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
python3 -m py_compile scripts/revalidation/native_wifi_pm_cnss_register_return_tracefs_live_v1100.py
python3 scripts/revalidation/native_wifi_pm_cnss_register_return_tracefs_live_v1100.py plan
python3 scripts/revalidation/native_wifi_pm_cnss_register_return_tracefs_live_v1100.py \
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
decision: v1100-cnss-pm-register-blocks-after-code1-mdm3-still-offline
pass: True
selftest: fail=0
```
