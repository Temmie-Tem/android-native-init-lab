# Native Init V1101 PM Server Register Path Tracefs Report

## Summary

V1101 passed. The V1095 provider-positive PM observer window was replayed while
tracefs-only uprobes were armed on both `libperipheral_client.so` and
`pm-service`.

Decision:

```text
v1101-cnss-server-register-no-return-at-pm_server_register_entry
```

`pm-proxy` remains the positive control: it enters `pm_client_register`, reaches
the `pm-service` register implementation, hits match/permission/state/add-client
checkpoints, returns `0x0`, then calls connect and returns `0x0`.

In the same window, `cnss-daemon` enters `pm_client_register` with
`peripheral="modem"` and `client="cnss-daemon"`. The matching Binder server
thread enters the `pm-service` register implementation at `0x6048`, but no later
server checkpoint is observed before bounded cleanup. This narrows the blocker
to the earliest `pm-service` register path, before supported-peripheral match at
`0x60cc`.

## Evidence

| item | path |
| --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_pm_server_register_path_tracefs_live_v1101.py` |
| predecessor evidence | `tmp/wifi/v1095-pm-cnss-voter-surface-live/manifest.json` |
| live evidence | `tmp/wifi/v1101-pm-server-register-path-tracefs-live/manifest.json` |
| live summary | `tmp/wifi/v1101-pm-server-register-path-tracefs-live/summary.md` |
| collector transcript | `tmp/wifi/v1101-pm-server-register-path-tracefs-live/host/pm-server-register-path-tracefs-observer.txt` |

## Result

```text
tracefs_result: tracefs-uprobe-pass
hit_count: 17
cnss_daemon_hit_count: 1
pm_server_event_hit_count: 12
per_mgr_binder_server_hit_count: 12
per_mgr_pid: 2193
mdm3_state: OFFLINING
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

Client register arguments:

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

CNSS server-side register classification:

```json
{
  "cnss_server_register_comms": [
    "Binder:2193_3"
  ],
  "cnss_server_register_hits_by_comm": {
    "Binder:2193_3": {
      "pm_server_register_entry": 1
    }
  }
}
```

Positive-control server-side register path:

```json
{
  "Binder:2193_2": {
    "pm_server_connect_ret": [
      "0x0"
    ],
    "pm_server_register_ret": [
      "0x0"
    ]
  },
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

## Interpretation

The PM chain is now narrowed below V1100:

```text
PM provider visible
  -> pm-proxy register returns 0
  -> pm-proxy connect returns 0
  -> cnss-daemon client register enters
  -> pm-service server register entry hit
  -> no pm-service register match at 0x60cc
  -> no pm-service permission/state/add-client/return checkpoint
  -> cnss-daemon register does not return
  -> cnss-daemon never calls connect/vote
  -> mdm3 still OFFLINING
  -> WLFW service 69 absent
  -> wlan0 absent
```

The old V1100 argument labels were semantically reversed in the report text.
V1101 uses the corrected interpretation: first PM client string is
`peripheral="modem"`, second string is `client="cnss-daemon"` or
`client="PM-PROXY-THREAD"`.

The next gate should trace the first instructions below `pm-service` register
entry, before `0x60cc`. The likely targets are String8/String16 argument access,
supported peripheral list iteration, and early Binder caller context handling.

## Safety

- No Wi-Fi HAL, scan/connect/link-up, DHCP, route, credential use, or external
  ping executed.
- No `mdm_helper` executed.
- No eSoC open/ioctl, GPIO write, partition write, flash, or reboot executed.
- No BPF attach executed.
- Tracefs events were removed cleanly; no register/enable/cleanup failure
  remained in the passing run.
- Device remained healthy: post-run `selftest` reported `fail=0`; `netservice`
  stayed USB-local.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_server_register_path_tracefs_live_v1101.py
python3 scripts/revalidation/native_wifi_pm_server_register_path_tracefs_live_v1101.py \
  --out-dir tmp/wifi/v1101-plan-validation \
  plan
python3 scripts/revalidation/native_wifi_pm_server_register_path_tracefs_live_v1101.py \
  --allow-tracefs-mount \
  --allow-tracefs-write \
  --allow-vendor-mount \
  --allow-selinuxfs-mount \
  --allow-pm-service-trigger-observer \
  --allow-cnss-daemon-start \
  --assume-yes \
  run
```

Result:

```text
decision: v1101-cnss-server-register-no-return-at-pm_server_register_entry
pass: True
selftest: fail=0
```
