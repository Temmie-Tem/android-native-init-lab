# WSTA184 Seccomp Expiring Execute Handoff

Date: 2026-07-05 15:19 KST

## Verdict

WSTA184 adds a host-only expiring handoff for the WSTA181 execution command.
It runs WSTA183 to refresh WSTA181 source-gate/readiness evidence, validates the
fresh WSTA182 command packet, then emits a short-lived WSTA181 execution
handoff.  It does not execute WSTA181.

Result: PASS.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta184_seccomp_expiring_execute_handoff.py`.
- Added focused tests in
  `tests/test_server_distro_wsta184_seccomp_expiring_execute_handoff.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta184-seccomp-expiring-execute-handoff-20260705T151924KST/
```

Decision:

```text
wsta184-seccomp-expiring-execute-handoff-pass
```

Fresh WSTA183 readiness:

```text
workspace/private/runs/server-distro/wsta184-seccomp-expiring-execute-handoff-20260705T151924KST/fresh-wsta183-readiness/wsta183_result.json
wsta183-seccomp-fresh-readiness-status-pass
```

Generated handoff:

```text
workspace/private/runs/server-distro/wsta184-seccomp-expiring-execute-handoff-20260705T151924KST/wsta184_expiring_wsta181_execute_handoff.json
state=READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY
executed=false
expires_utc=20260705T063425Z
```

Wrapped WSTA181 command:

```text
workspace/private/runs/server-distro/wsta184-seccomp-expiring-execute-handoff-20260705T151924KST/fresh-wsta183-readiness/fresh-wsta182-readiness-status/wsta182_wsta181_execute_command.json
workspace/private/runs/server-distro/wsta184-seccomp-expiring-execute-handoff-20260705T151924KST/fresh-wsta183-readiness/fresh-wsta182-readiness-status/wsta182_wsta181_execute_command.sh
```

## Checks

```text
fresh_readiness_valid=true
paths_valid=true
freshness_valid=true
readiness_valid=true
command_valid=true
age_sec=0
max_age_sec=900
spread_sec=0
command_targets_wsta181=true
correct_token_literal_absent=true
no_external_network_inputs=true
```

## Safety Boundary

This unit did not flash, reboot, connect Wi-Fi, run DHCP, open a public tunnel,
mutate packet filters, write userdata, switch root, execute WSTA181, execute
WSTA178, execute WSTA177, execute WSTA175, execute WSTA170, execute
WSTA168/WSTA167, load a seccomp filter, enforce seccomp, or supply the correct
WSTA161 token.  WSTA184 only generated a private expiring handoff.

## Validation

- `py_compile`:
  - `run_wsta184_seccomp_expiring_execute_handoff.py`
  - `test_server_distro_wsta184_seccomp_expiring_execute_handoff.py`
- Focused WSTA183 + WSTA184 tests: `8 tests OK`.
- WSTA184 expiring handoff proof against the current WSTA180 handoff bundle:
  pass.
- Full server-distro regression: `639 tests OK`.

## Next

WSTA184 is now the freshest bounded execution handoff.  Any future live
execution gate should consume this handoff and reject it after expiry, rather
than executing an unbounded WSTA182 command packet directly.
