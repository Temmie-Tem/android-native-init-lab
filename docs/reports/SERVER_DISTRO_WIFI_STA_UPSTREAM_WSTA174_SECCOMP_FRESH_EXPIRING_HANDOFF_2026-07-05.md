# WSTA174 Seccomp Fresh Expiring Handoff Pass

Date: 2026-07-05 14:26 KST

## Verdict

WSTA174 adds a one-shot host runner that refreshes the pre-execution packet and
wraps it in an expiring handoff in the same private run directory.  It runs
WSTA172, then WSTA173, and does not execute WSTA170.

Result: PASS.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta174_seccomp_fresh_expiring_handoff.py`.
- Added focused tests in
  `tests/test_server_distro_wsta174_seccomp_fresh_expiring_handoff.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta174-seccomp-fresh-expiring-handoff-20260705T142628KST/
```

Decision:

```text
wsta174-seccomp-fresh-expiring-handoff-pass
```

Nested results:

```text
wsta172-fresh-execute-preflight/wsta172_result.json  wsta172-seccomp-fresh-execute-preflight-pass
wsta173-expiring-handoff/wsta173_result.json         wsta173-seccomp-expiring-execute-handoff-pass
```

Generated handoff:

```text
workspace/private/runs/server-distro/wsta174-seccomp-fresh-expiring-handoff-20260705T142628KST/wsta173-expiring-handoff/wsta173_expiring_execute_handoff.json
```

Handoff state:

```text
state=READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY
executed=false
expires_utc=20260705T054136Z
age_sec=0
max_age_sec=900
```

## Safety Boundary

This unit did not flash, reboot, connect Wi-Fi, run DHCP, open a public tunnel,
mutate packet filters, write userdata, switch root, execute WSTA170, execute
WSTA168/WSTA167, load a seccomp filter, enforce seccomp, or supply the correct
WSTA161 token.  Device contact was limited to the nested WSTA172/WSTA169
read-only bridge/version/status/selftest checks.

## Validation

- `py_compile`:
  - `run_wsta174_seccomp_fresh_expiring_handoff.py`
  - `test_server_distro_wsta174_seccomp_fresh_expiring_handoff.py`
- Focused WSTA173 + WSTA174 tests: `8 tests OK`.
- WSTA174 one-shot fresh expiring handoff proof against the current
  bridge/device: pass.
- Full server-distro regression: `599 tests OK`.

## Next

If the WSTA174 handoff is expired, rerun WSTA174.  If it is still fresh, it
points at the exact WSTA170 execution command, which still requires explicit
operator approval for the no-load live observation.
