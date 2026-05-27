# Native Init V1167 PM-Service Action Branch Live Report

Date: `2026-05-27`

## Result

- Decision: `v1167-state-transition-called-but-no-esoc0`
- Pass: `true`
- Plan: `docs/plans/NATIVE_INIT_V1167_PM_ACTION_BRANCH_LIVE_PLAN_2026-05-27.md`
- V401 evidence: `tmp/wifi/v1167-v401-selinuxfs-mount/manifest.json`
- V490 evidence: `tmp/wifi/v1167-v490-policy-load/manifest.json`
- Live evidence: `tmp/wifi/v1167-pm-action-branch-live-after-v490/manifest.json`
- Live summary: `tmp/wifi/v1167-pm-action-branch-live-after-v490/summary.md`

## Summary

V1167 removes the main V1166 ambiguity.  Native does not skip the fresh
state transition because of stale voter count or reconnect state.  The first
`pm-service` Binder connect sees old voters `0`, increments to `1`, sees
reconnect flag `0`, and calls the state helper with `state=2`.  Even so,
`pm-service` never opens `/dev/subsys_esoc0`.

The remaining blocker is below `pm-service` state helper `0x92dc`: the client
callback dispatch path runs, but its side effect does not match Android's
`__subsystem_get(esoc0)` path.

## Key Evidence

| key | value |
| --- | --- |
| decision | `v1167-state-transition-called-but-no-esoc0` |
| action branch event count | `10` |
| first voters before/after | `0 -> 1` |
| second voters before/after | `1 -> 2` |
| reconnect flags | `[0]` |
| state helper call | `state=2`, entry `0xb400007fb7426180` |
| later state transitions | `state=3`, `state=0`, `state=1` |
| late `pm-proxy` | alive for all 12 polls |
| `pm-service` `/dev/subsys_modem` | count `1` in every late poll |
| `pm-service` `/dev/subsys_esoc0` | count `0` in every late poll |
| MHI/WLFW/BDF/`wlan0` | all `0` |
| Wi-Fi HAL/scan/connect/credentials | not executed |
| DHCP/route/external ping | not executed |

## Interpretation

The PM server contract is now positive through the action branch:

```text
pm-proxy connect
  -> pm-service connect implementation
    -> old voter count 0
    -> reconnect flag 0
    -> state helper 0x92dc(state=2)
      -> no /dev/subsys_esoc0
```

So the next probe should move below `0x92dc`, not reorder `pm-proxy` or repeat
the same late-start gate.

## Next Gate

V1168 should trace the state helper client-callback dispatch:

- `0x93bc`: list client pointer and state before dispatch.
- `0x8630`: callback wrapper entry, client record and state.
- `0x8640`/`0x8644`: resolved callback target pointer before `br x2`.
- `pm-service` maps during the same window, so the callback target can be
  mapped to its binary region.

If the callback target is valid but no eSoC open follows, the next split is
inside the target callback.  If the callback list is empty or points to the
wrong client, the issue is PM-service client registration parity.

## Validation

- `python3 -m py_compile scripts/revalidation/native_wifi_pm_action_branch_live_v1167.py`
- `python3 scripts/revalidation/native_wifi_pm_action_branch_live_v1167.py plan`
- V401 selinuxfs mount proof passed.
- V490 SELinux policy load proof passed.
- V1167 live gate passed.
- Post-cleanup native health:
  - `version`: `A90 Linux init 0.9.68 (v724)`
  - `selftest`: `pass=11 warn=1 fail=0`
  - `netservice`: disabled, `ncm0=absent`, `tcpctl=stopped`
