# Native Init V1177 PM Dependency Flag Live Report

Date: `2026-05-27`

## Result

- Decision: `v1177-dependency-flag-not-armed`
- Pass: `true`
- Plan: `docs/plans/NATIVE_INIT_V1177_PM_DEPENDENCY_FLAG_LIVE_PLAN_2026-05-27.md`
- V401 evidence: `tmp/wifi/v1177-v401-selinuxfs-mount/manifest.json`
- V490 evidence: `tmp/wifi/v1177-v490-policy-load/manifest.json`
- Live evidence: `tmp/wifi/v1177-pm-dependency-flag-live-after-v490/manifest.json`
- Live summary: `tmp/wifi/v1177-pm-dependency-flag-live-after-v490/summary.md`

## Summary

V1177 traced the PM-service dependency path selected by V1176.  The result is
more precise than the V1176 host-only hypothesis: native does not arm the
dependency flag late.  Instead, when state `0` arrives after the state `2`/`3`
sequence, the dependency object is already in state `1`, so PM-service skips the
dependency state-0 call, wait path, and flag-set path.

| key | value |
| --- | --- |
| decision | `v1177-dependency-flag-not-armed` |
| native state order | `[2, 3, 0, 1]` |
| state-2 dependency flag | `[0]` |
| fd `8` target | `/tmp/a90-v231-1089/root/dev/subsys_modem` |
| state-0 dependency state checks | `1`, `1` |
| state-0 dependency state-0 call | `0` |
| state-0 wait path | `0` |
| state-0 flag-set path | `0` |
| state-2 dependency/eSoC call | `0` |
| mss after observer | `ONLINE` |
| mdm3 after observer | `OFFLINING` |

## Interpretation

The current native PM ordering is:

```text
state=2
  -> dependency_flag=0
  -> skip dependency state=2 call
  -> open /dev/subsys_modem
  -> set state=3

state=3
  -> no-op return

state=0
  -> dependency state is already 1
  -> skip dependency state-0 call/wait
  -> do not set dependency flag
  -> set state=1
```

So the missing condition is not merely "wait longer after state `0`."  The
dependency relationship exists, but native never reaches the dependency call or
flag-set paths that would make a later state `2` call the dependency/eSoC
branch.  Android-good still reaches `pm-service` `__subsystem_get(esoc0)` before
WLFW/BDF/`wlan0`, so the next blocker is the PM dependency object's initial
state/order parity.

## Key Evidence

| label | count | value |
| --- | --- | --- |
| `pm_dep_state0_entry` | `1` | state `0` branch entered |
| `pm_dep_state0_dependency_present` | `1` | dependency path present |
| `pm_dep_state0_dependency_state_first` | `1` | dependency state `1` |
| `pm_dep_state0_dependency_state_second` | `1` | dependency state `1` |
| `pm_dep_state0_dependency_state0_call` | `0` | not reached |
| `pm_dep_state0_wait_call` | `0` | not reached |
| `pm_dep_state0_flag_set` | `0` | not reached |
| `pm_dep_state2_dependency_state2_call` | `0` | not reached |

## Next Gate

V1178 should classify PM dependency object initialization/order parity:

- identify which dependency object corresponds to eSoC/mdm3 in Android-good
  versus native
- compare Android/native dependency state before the first state-2 ack
- trace or classify the PM event that should put the dependency into state
  `2`/`3` before the parent state-0/state-2 sequence
- avoid another broad `pm-proxy` retry; keep Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  and flash blocked until `/dev/subsys_esoc0` or WLFW appears

## Validation

- `python3 -m py_compile scripts/revalidation/native_wifi_pm_dependency_flag_live_v1177.py`
- `python3 scripts/revalidation/native_wifi_pm_dependency_flag_live_v1177.py plan`
- V401 selinuxfs mount proof passed.
- V490 SELinux policy load proof passed.
- V1177 live gate passed.
- Post-cleanup native health:
  - `version`: `A90 Linux init 0.9.68 (v724)`
  - `selftest`: `pass=11 warn=1 fail=0`
  - `netservice`: disabled, `ncm0=absent`, `tcpctl=stopped`
