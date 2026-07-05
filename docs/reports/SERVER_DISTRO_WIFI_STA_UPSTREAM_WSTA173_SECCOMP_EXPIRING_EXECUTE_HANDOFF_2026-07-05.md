# WSTA173 Seccomp Expiring Execute Handoff Pass

Date: 2026-07-05 14:22 KST

## Verdict

WSTA173 consumes the WSTA172 fresh pre-execution proof, revalidates the nested
WSTA169/WSTA170/WSTA171 artifacts and the generated WSTA170 command, then emits
an expiring handoff packet.  It does not execute the command.

Result: PASS.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta173_seccomp_expiring_execute_handoff.py`.
- Added focused tests in
  `tests/test_server_distro_wsta173_seccomp_expiring_execute_handoff.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta173-seccomp-expiring-execute-handoff-20260705T142900KST/
```

Decision:

```text
wsta173-seccomp-expiring-execute-handoff-pass
```

Generated handoff:

```text
workspace/private/runs/server-distro/wsta173-seccomp-expiring-execute-handoff-20260705T142900KST/wsta173_expiring_execute_handoff.json
```

Handoff state:

```text
state=READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY
executed=false
expires_utc=20260705T052930Z
age_sec=463
max_age_sec=900
```

## Revalidated Inputs

WSTA173 revalidated:

- WSTA172 proof:
  `workspace/private/runs/server-distro/wsta172-seccomp-fresh-execute-preflight-20260705T142100KST/wsta172_result.json`.
- WSTA169 readiness result inside that proof.
- WSTA170 source-gate result inside that proof.
- WSTA171 execution-preflight result inside that proof.
- WSTA171 generated command JSON and script.

All path, freshness, WSTA172, nested-result, and command checks were true.

## Safety Boundary

This unit did not flash, reboot, connect Wi-Fi, run DHCP, open a public tunnel,
mutate packet filters, write userdata, switch root, execute WSTA170, execute
WSTA168/WSTA167, load a seccomp filter, enforce seccomp, or supply the correct
WSTA161 token.

## Validation

- `py_compile`:
  - `run_wsta173_seccomp_expiring_execute_handoff.py`
  - `test_server_distro_wsta173_seccomp_expiring_execute_handoff.py`
- Focused WSTA172 + WSTA173 tests: `8 tests OK`.
- WSTA173 expiring handoff proof against the WSTA172 fresh pre-execution
  artifact: pass.
- Full server-distro regression: `595 tests OK`.

## Next

If the handoff is expired, rerun WSTA172 before execution.  If it is still
fresh, the handoff points at the exact WSTA170 execution command, which still
requires explicit operator approval for the no-load live observation.
