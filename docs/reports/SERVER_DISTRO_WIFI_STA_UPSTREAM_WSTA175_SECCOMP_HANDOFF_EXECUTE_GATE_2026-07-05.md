# WSTA175 Seccomp Handoff Execute Gate

Date: 2026-07-05 14:31 KST

## Verdict

WSTA175 adds the handoff-aware executor gate for the WSTA173/WSTA174 expiring
handoff.  By default it validates the handoff, command artifacts, and freshness,
then stops before execution.  Only the full WSTA175 acknowledgement set executes
the contained WSTA170 command.

Result: SOURCE GATE PASS.  The real WSTA174 handoff validated, then the runner
stopped with:

```text
wsta175-blocked-explicit-execution-gate-required
```

No WSTA170 command was executed in this unit.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta175_seccomp_handoff_execute_gate.py`.
- Added focused tests in
  `tests/test_server_distro_wsta175_seccomp_handoff_execute_gate.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta175-seccomp-handoff-execute-source-gate-20260705T143400KST/
```

Input handoff:

```text
workspace/private/runs/server-distro/wsta174-seccomp-fresh-expiring-handoff-20260705T142628KST/wsta173-expiring-handoff/wsta173_expiring_execute_handoff.json
```

Checks:

```text
handoff_valid=true
handoff_fresh=true
command_artifacts_valid=true
explicit_execution_gate=false
```

Freshness at proof time:

```text
expires_utc=20260705T054136Z
seconds_remaining=604
```

## Execution Gate

WSTA175 requires all of these before executing:

```text
--execute-wsta175-handoff
--allow-wsta170-command-execution
--ack-handoff-fresh
--ack-no-correct-wsta161-token
--ack-no-seccomp-load
--ack-cleanup-required
```

When executed, WSTA175 runs the handoff-contained WSTA170 command and requires
the WSTA170 result to pass with nested WSTA167 pass, cleanup OK, final selftest
fail-zero, no seccomp load/enforcement, no correct WSTA161 token, no flash, no
reboot, no Wi-Fi connect, no DHCP, no public tunnel, and no packet-filter
mutation.

## Safety Boundary

This unit did not flash, reboot, connect Wi-Fi, run DHCP, open a public tunnel,
mutate packet filters, write userdata, switch root, execute WSTA170, execute
WSTA168/WSTA167, load a seccomp filter, enforce seccomp, or supply the correct
WSTA161 token.

## Validation

- `py_compile`:
  - `run_wsta175_seccomp_handoff_execute_gate.py`
  - `test_server_distro_wsta175_seccomp_handoff_execute_gate.py`
- Focused WSTA174 + WSTA175 tests: `8 tests OK`.
- WSTA175 source-gate proof against the real WSTA174 handoff: blocked before
  execution as designed, handoff/command/freshness checks true.
- Full server-distro regression: `603 tests OK`.

## Next

If the handoff expires, rerun WSTA174 first.  If it is still fresh, WSTA175 is
the exact executor surface for the no-load live observation, still requiring
explicit operator approval.
