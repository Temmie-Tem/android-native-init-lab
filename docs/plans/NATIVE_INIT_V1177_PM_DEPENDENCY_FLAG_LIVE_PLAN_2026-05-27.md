# Native Init V1177 PM Dependency Flag Live Plan

Date: `2026-05-27`

## Goal

Trace the PM-service dependency flag path selected by V1176.  V1176 showed that
native state `2` skips the dependency/eSoC branch because dependency flag is
`0`, then state `3` returns as a no-op.  V1177 verifies whether the state-0 path
arms that dependency flag only after the state-2 opportunity has already passed.

## Preconditions

- Native v724 is healthy.
- Serial bridge is available on `127.0.0.1:54321`.
- V401 selinuxfs mount and V490 policy-load proof are rerun in the same boot.
- Helper `a90_android_execns_probe v217` remains deployed.
- V1176 decision is `v1176-dependency-flag-state-order-gap-classified`.

## Added Uprobes

| label | binary | offset | purpose |
| --- | --- | --- | --- |
| `pm_dep_state0_entry` | `pm-service` | `0x8a10` | state-0 branch entry |
| `pm_dep_state0_dependency_present` | `pm-service` | `0x8a74` | dependency object path |
| `pm_dep_state0_dependency_state_first` | `pm-service` | `0x8a94` | first dependency-state check |
| `pm_dep_state0_dependency_state_second` | `pm-service` | `0x8ab8` | second dependency-state check |
| `pm_dep_state0_dependency_state0_call` | `pm-service` | `0x8b04` | dependency state-0 call |
| `pm_dep_state0_wait_call` | `pm-service` | `0x8b30` | dependency wait call |
| `pm_dep_state0_wait_return` | `pm-service` | `0x8b34` | wait return |
| `pm_dep_state0_post_wait_state` | `pm-service` | `0x8b78` | post-wait dependency state |
| `pm_dep_state0_flag_set` | `pm-service` | `0x8b94` | dependency flag setter |
| `pm_dep_state2_dependency_state2_call` | `pm-service` | `0x8980` | state-2 dependency/eSoC call if reached |

## Success Criteria

- Manifest decision is one of:
  - `v1177-state0-arms-dependency-after-state2-gap`
  - `v1177-state2-dependency-call-observed`
  - `v1177-dependency-flag-not-armed`
  - `v1177-dependency-trace-missing`
- V1175 state-2 open/fd-target behavior is reproduced.
- State-0 dependency flag setter and state-2 dependency call status are recorded.
- Cleanup returns to native v724 health.
- No Wi-Fi HAL, scan/connect, credential use, DHCP, route, external ping,
  partition write, boot image write, or flash is performed.

## Next Branch

If state-0 arms the flag after state-2 already skipped dependency, the next
work is not another broad PM retry.  The next step is a narrow ordering repair:
make the dependency flag/state-0 path happen before the first state-2 ack, then
observe whether PM-service calls the dependency state-2 branch and reaches
`/dev/subsys_esoc0`.
