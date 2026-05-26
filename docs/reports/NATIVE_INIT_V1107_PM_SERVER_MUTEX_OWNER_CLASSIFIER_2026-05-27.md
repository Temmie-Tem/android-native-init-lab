# Native Init V1107 PM Server Mutex Owner Classifier Report

## Summary

V1107 passed. It performed host-only analysis of the V1106 live evidence and
reconstructed the modem record mutex owner before the CNSS futex wait.

Decision:

```text
v1107-modem-mutex-owner-blocked-in-subsystem-get
```

The owner is `Binder:15867_2` / TID `15872`. That thread acquired the modem
record mutex at return offset `0x87c8` in `pm-service`, did not release it
before the CNSS wait timestamp, and later sampled in `__subsystem_get` and
`_request_firmware`. CNSS TID `19620` then waited in futex on the same mutex.

## Evidence

| item | path |
| --- | --- |
| classifier | `scripts/revalidation/native_wifi_pm_server_mutex_owner_classifier_v1107.py` |
| predecessor evidence | `tmp/wifi/v1106-pm-server-wchan-tracefs-live/manifest.json` |
| host evidence | `tmp/wifi/v1107-pm-server-mutex-owner-classifier/manifest.json` |
| summary | `tmp/wifi/v1107-pm-server-mutex-owner-classifier/summary.md` |
| owner disassembly | `tmp/wifi/v1107-pm-server-mutex-owner-classifier/host/pm-service-owner-disassembly.txt` |

## Result

Owner:

```json
{
  "comm": "Binder:15867_2",
  "tid": "15872",
  "mutex": "0xb400007f7dc26198",
  "return_offset": "0x87c8",
  "ret": "0x0"
}
```

Owner wait state:

```json
{
  "states": ["D", "S"],
  "wchans": [
    "__subsystem_get",
    "_request_firmware",
    "binder_ioctl_write_read"
  ],
  "syscalls": ["29", "56"]
}
```

CNSS waiter:

```json
{
  "comm": "Binder:15867_3",
  "tid": "19620",
  "mutex": "0xb400007f7dc26198",
  "wchans": [
    "binder_ioctl_write_read",
    "futex_wait_queue_me"
  ],
  "syscalls": ["29", "98"]
}
```

## Interpretation

The immediate blocker is no longer simply "CNSS register blocks". The more
precise chain is:

```text
pm-proxy positive control
  -> pm-service Binder:15867_2 acquires modem record mutex
  -> return offset 0x87c8 enters the pm-service state/action function
  -> owner thread blocks in __subsystem_get/_request_firmware while holding mutex
  -> cnss-daemon Binder:15867_3 reaches same modem record mutex
  -> CNSS waits in futex_wait_queue_me
  -> cnss-daemon register does not return
  -> cnss-daemon never calls connect/vote
  -> mdm3 still OFFLINING
  -> WLFW service 69 absent
  -> wlan0 absent
```

Disassembly around `0x87c8` shows the owner return is immediately after
`pthread_mutex_lock@plt` in a function that keeps the modem record mutex until a
later `pthread_mutex_unlock@plt` path near `0x8d20`. The owner blocks before
reaching that unlock path.

The next gate should stop using a pre-CNSS `per_proxy` connect as a harmless
positive control. It is now proven to hold the modem record mutex while waiting
for lower subsystem/firmware progress. The closest next experiment is a bounded
PM ordering test that starts the provider and `cnss-daemon` without the
pre-CNSS `per_proxy` connect, or delays `per_proxy` connect until after CNSS
register progress is observed.

## Safety

- Host-only analysis: no device command executed.
- No tracefs write, BPF attach, PM actor, `cnss-daemon` start, Wi-Fi HAL,
  scan/connect/link-up, DHCP, route, credential use, or external ping executed.
- No eSoC open/ioctl, GPIO write, partition write, flash, or reboot executed.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_server_mutex_owner_classifier_v1107.py
python3 scripts/revalidation/native_wifi_pm_server_mutex_owner_classifier_v1107.py \
  --out-dir tmp/wifi/v1107-plan-validation \
  plan
python3 scripts/revalidation/native_wifi_pm_server_mutex_owner_classifier_v1107.py run
```

Result:

```text
decision: v1107-modem-mutex-owner-blocked-in-subsystem-get
pass: True
device_command_executed: False
```
