# Native Init V1106 PM Server Wchan Tracefs Report

## Summary

V1106 passed. The V1095 provider-positive PM observer window was replayed while
tracefs-only raw mutex uprobes remained armed and `pm-service` threads were
sampled through `/proc/<pid>/task/<tid>/wchan` during the live child window.

Decision:

```text
v1106-cnss-raw-lock-pending-in-futex-wait
```

The CNSS Binder thread that issued the raw `pthread_mutex_lock@plt` call on the
modem record mutex was sampled in sleep state with `wchan=futex_wait_queue_me`.
This confirms the V1105 blocker is a real pthread mutex wait, not only a trace
return-pairing artifact.

## Evidence

| item | path |
| --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_pm_server_wchan_tracefs_live_v1106.py` |
| predecessor evidence | `tmp/wifi/v1105-pm-server-raw-mutex-tracefs-live/manifest.json` |
| live evidence | `tmp/wifi/v1106-pm-server-wchan-tracefs-live/manifest.json` |
| live summary | `tmp/wifi/v1106-pm-server-wchan-tracefs-live/summary.md` |
| collector transcript | `tmp/wifi/v1106-pm-server-wchan-tracefs-live/host/pm-server-wchan-tracefs-observer.txt` |

## Result

```text
tracefs_result: tracefs-uprobe-pass
thread_sample_count: 270
cnss_daemon_hit_count: 1
pm_server_event_hit_count: 201
per_mgr_binder_server_hit_count: 136
mdm3_state: OFFLINING
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

CNSS pending thread:

```json
{
  "comm": "Binder:15867_3",
  "tid": "19620",
  "mutex": "0xb400007f7dc26198",
  "wchan": [
    "binder_ioctl_write_read",
    "futex_wait_queue_me"
  ],
  "state": [
    "S"
  ]
}
```

Positive control:

```text
connect_complete_comms: ["Binder:15867_2"]
cnss_server_register_last_label: pm_server_name_helper_lock_call
```

## Interpretation

The PM chain is now narrowed to an actual futex wait on the modem record mutex:

```text
PM provider visible
  -> pm-proxy register succeeds
  -> pm-proxy connect helper locks modem mutex
  -> pm-proxy connect helper unlocks modem mutex
  -> pm-proxy connect returns 0
  -> cnss-daemon client register enters
  -> cnss-daemon reaches modem record helper
  -> cnss-daemon calls pthread_mutex_lock(modem mutex)
  -> CNSS Binder TID samples wchan=futex_wait_queue_me
  -> cnss-daemon register does not return
  -> cnss-daemon never calls connect/vote
  -> mdm3 still OFFLINING
  -> WLFW service 69 absent
  -> wlan0 absent
```

The next gate should classify why the modem record mutex remains unavailable:

- inspect owner/lifetime through mutex internals if a safe read-only route is
  available,
- compare `pm-service` record initialization and lock ordering between the
  `pm-proxy` positive path and the CNSS register path,
- or test a minimal ordering repair that initializes/unblocks the modem record
  before CNSS register without starting Wi-Fi HAL or scan/connect.

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
python3 -m py_compile scripts/revalidation/native_wifi_pm_server_wchan_tracefs_live_v1106.py
python3 scripts/revalidation/native_wifi_pm_server_wchan_tracefs_live_v1106.py \
  --out-dir tmp/wifi/v1106-plan-validation \
  plan
python3 scripts/revalidation/native_wifi_pm_server_wchan_tracefs_live_v1106.py \
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
decision: v1106-cnss-raw-lock-pending-in-futex-wait
pass: True
selftest: fail=0
```
