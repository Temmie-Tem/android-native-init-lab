# Native Init V1167 PM-Service Action Branch Live Plan

Date: `2026-05-27`

## Goal

Run the V1165 bounded late `pm-proxy` gate with additional `pm-service`
action-branch uprobes selected by V1166.  The goal is to explain why native
PM connect/start-vote returns success but does not create Android's
`/dev/subsys_esoc0` side effect.

## Preconditions

- Device is native v724 and selftest has no failures.
- Serial bridge is available on `127.0.0.1:54321`.
- Helper `a90_android_execns_probe v217` is already deployed or the live gate
  fails its remote marker/SHA check.
- V401 selinuxfs mount and V490 policy-load proof are rerun in the same boot
  before the live gate.

## Added Uprobes

The live runner uses `x` register fetchargs for tracefs compatibility; `x8`
and `x9` are interpreted as the low 32-bit `w8`/`w9` values from the V1166
branch model.

| label | offset | fetch |
| --- | --- | --- |
| `pm_server_connect_vote_count_before` | `0x9738` | `voters_before=%x8` |
| `pm_server_connect_vote_count_after_store` | `0x9740` | `voters_before=%x8 voters_after=%x9` |
| `pm_server_connect_reconnect_flag_check` | `0x9748` | `reconnect_flag=%x8` |
| `pm_server_connect_powerup_state_call` | `0x97dc` | `entry=%x0 state=%x1` |
| `pm_server_state_transition_entry` | `0x92dc` | `entry=%x0 state=%x1` |

## Success Criteria

- Manifest decision is one of:
  - `v1167-old-voter-count-skips-state-transition`
  - `v1167-reconnect-flag-skips-state-transition`
  - `v1167-state-transition-called-but-no-esoc0`
  - `v1167-action-branch-esoc0-advanced`
  - `v1167-action-branch-no-state-call-unclassified`
- `pm_action_branch.event_count > 0`.
- Cleanup returns to native v724 health.
- No Wi-Fi HAL, scan/connect, credential use, DHCP, route, external ping,
  partition write, boot image write, flash, or non-clean reboot is performed.

## Next Branches

- Old voter count nonzero: adjust PM actor ordering or classify stale voter
  reset semantics.
- Reconnect flag nonzero: classify PM reconnect/timer state initialization.
- State helper called but no eSoC: trace the state helper client callback and
  open path below `0x92dc`.
- eSoC observed: preserve evidence and gate the next lower MHI/WLFW step.
