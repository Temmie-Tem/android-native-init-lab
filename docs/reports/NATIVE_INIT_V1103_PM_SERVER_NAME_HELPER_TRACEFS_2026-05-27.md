# Native Init V1103 PM Server Name Helper Tracefs Report

## Summary

V1103 passed. The V1095 provider-positive PM observer window was replayed while
tracefs-only instruction uprobes were armed inside `pm-service` helper `0x9538`.

Decision:

```text
v1103-cnss-server-register-no-return-at-pm_server_name_helper_lock_call
```

`pm-proxy` remains the positive control. It locks and unlocks the `SDX50M`
record mutex, then locks and unlocks the `modem` record mutex, matches
`modem`, and completes PM register/connect.

`cnss-daemon` also locks/unlocks the first `SDX50M` record. It then reaches the
second/modem record, derives the mutex address `entry + 0x18`, calls
`pthread_mutex_lock`, and never reaches the lock-return checkpoint before
bounded cleanup. This confirms the immediate blocker is a mutex wait on the
modem supported-peripheral record inside `pm-service`.

## Evidence

| item | path |
| --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_pm_server_name_helper_tracefs_live_v1103.py` |
| predecessor evidence | `tmp/wifi/v1102-pm-server-early-register-tracefs-live/manifest.json` |
| live evidence | `tmp/wifi/v1103-pm-server-name-helper-tracefs-live/manifest.json` |
| live summary | `tmp/wifi/v1103-pm-server-name-helper-tracefs-live/summary.md` |
| collector transcript | `tmp/wifi/v1103-pm-server-name-helper-tracefs-live/host/pm-server-name-helper-tracefs-observer.txt` |

## Result

```text
tracefs_result: tracefs-uprobe-pass
hit_count: 139
cnss_daemon_hit_count: 1
pm_server_event_hit_count: 125
per_mgr_binder_server_hit_count: 89
per_mgr_pid: 3045
mdm3_state: OFFLINING
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

CNSS server-side helper classification:

```json
{
  "cnss_server_register_last_label": "pm_server_name_helper_lock_call",
  "cnss_server_register_hits_by_comm": {
    "Binder:3045_3": {
      "pm_server_register_name_helper_call": 2,
      "pm_server_name_helper_entry": 2,
      "pm_server_name_helper_mutex_addr": 2,
      "pm_server_name_helper_lock_call": 2,
      "pm_server_name_helper_lock_after": 1,
      "pm_server_name_helper_function_ret": 1
    }
  }
}
```

Critical trace excerpt:

```text
cnss-daemon path:
  first entry SDX50M:
    mutex=...26018
    lock_call -> lock_after -> unlock -> helper return
    strcmp SDX50M vs modem => nonzero

  second entry modem:
    mutex=...26198
    lock_call
    no lock_after
    no helper return
    no modem strcmp
    no register match
```

`pm-proxy` positive control proves the same `modem` mutex can be locked and
unlocked in the earlier actor path:

```text
pm-proxy path:
  second entry modem:
    mutex=...26198
    lock_call -> lock_after -> unlock -> helper return
    strcmp modem vs modem => 0
    register returns 0
    connect returns 0
```

## Interpretation

The PM chain is now narrowed below V1102:

```text
PM provider visible
  -> pm-proxy register/connect positive control succeeds
  -> cnss-daemon client register enters
  -> pm-service server register entry hit
  -> first supported entry SDX50M helper returns
  -> SDX50M != modem, loop advances
  -> second/modem entry helper starts
  -> pthread_mutex_lock(entry + 0x18) called
  -> lock does not return
  -> no modem strcmp/match for CNSS
  -> cnss-daemon register does not return
  -> cnss-daemon never calls connect/vote
  -> mdm3 still OFFLINING
  -> WLFW service 69 absent
  -> wlan0 absent
```

The next gate should classify why the modem record mutex remains locked or
unavailable for the CNSS Binder thread after `pm-proxy` completes. The likely
targets are `pm-service` connect/vote path lock ownership, Binder thread
lifetime after `pm-proxy`, or a missed unlock in a lower PM state transition.

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
python3 -m py_compile scripts/revalidation/native_wifi_pm_server_name_helper_tracefs_live_v1103.py
python3 scripts/revalidation/native_wifi_pm_server_name_helper_tracefs_live_v1103.py \
  --out-dir tmp/wifi/v1103-plan-validation \
  plan
python3 scripts/revalidation/native_wifi_pm_server_name_helper_tracefs_live_v1103.py \
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
decision: v1103-cnss-server-register-no-return-at-pm_server_name_helper_lock_call
pass: True
selftest: fail=0
```
