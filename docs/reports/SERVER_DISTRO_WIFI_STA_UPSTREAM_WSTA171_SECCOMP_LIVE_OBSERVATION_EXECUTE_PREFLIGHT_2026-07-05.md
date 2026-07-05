# WSTA171 Seccomp Live-Observation Execute Preflight Pass

Date: 2026-07-05 14:11 KST

## Verdict

WSTA171 consumes the WSTA170 source-gate proof plus the underlying WSTA169
readiness proof and WSTA168 command artifacts, revalidates all of them, and
emits the exact WSTA170 execution command packet for the no-load live
observation.

Result: PASS.  This unit is host-only and did not execute the generated command.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta171_seccomp_live_observation_execute_preflight.py`.
- Added focused tests in
  `tests/test_server_distro_wsta171_seccomp_live_observation_execute_preflight.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta171-seccomp-live-observation-execute-preflight-20260705T141100KST/
```

Decision:

```text
wsta171-seccomp-live-observation-execute-preflight-pass
```

Generated command artifacts:

```text
workspace/private/runs/server-distro/wsta171-seccomp-live-observation-execute-preflight-20260705T141100KST/wsta171_wsta170_execute_command.json
workspace/private/runs/server-distro/wsta171-seccomp-live-observation-execute-preflight-20260705T141100KST/wsta171_wsta170_execute_command.sh
```

Command state:

```text
schema=a90-wsta171-wsta170-execute-command-v1
state=READY_TO_RUN_NOT_EXECUTED
executed=false
required_ack_count=6
```

## Revalidated Inputs

WSTA171 revalidated:

- WSTA170 source-gate proof:
  `workspace/private/runs/server-distro/wsta170-seccomp-live-observation-execute-source-gate-20260705T140000KST/wsta170_result.json`.
- WSTA169 readiness proof:
  `workspace/private/runs/server-distro/wsta169-seccomp-live-readiness-readonly-20260705T135709KST/wsta169_result.json`.
- WSTA168 command JSON:
  `workspace/private/runs/server-distro/wsta168-seccomp-live-observation-preflight-20260705T1358KST/wsta168_live_command.json`.
- WSTA168 command script:
  `workspace/private/runs/server-distro/wsta168-seccomp-live-observation-preflight-20260705T1358KST/wsta168_live_command.sh`.

All source-gate, readiness, WSTA168 command, and WSTA171 execution-command
checks were true.

## Execution Command

The generated WSTA170 execution command includes:

```text
--execute-wsta170-no-load-live-observation
--allow-wsta168-command-execution
--ack-readiness-proof-current
--ack-no-correct-wsta161-token
--ack-no-seccomp-load
--ack-cleanup-required
```

Expected outcome remains:

```text
decision=wsta170-seccomp-live-observation-execute-pass
nested_decision=wsta167-seccomp-live-observation-pass
seccomp_filter_loaded=false
seccomp_enforced=false
correct_wsta161_token_supplied=false
```

## Safety Boundary

This unit did not flash, reboot, connect Wi-Fi, run DHCP, open a public tunnel,
mutate packet filters, write userdata, switch root, execute WSTA170, execute
WSTA168/WSTA167, load a seccomp filter, enforce seccomp, or supply the correct
WSTA161 token.

## Validation

- `py_compile`:
  - `run_wsta171_seccomp_live_observation_execute_preflight.py`
  - `test_server_distro_wsta171_seccomp_live_observation_execute_preflight.py`
- Focused WSTA170 + WSTA171 tests: `7 tests OK`.
- WSTA171 preflight generation from the real WSTA170/WSTA169/WSTA168 artifacts:
  pass.
- Full server-distro regression: `587 tests OK`.

## Next

The generated WSTA171 command is the exact next execution step, but it must only
be run with explicit operator approval for the no-load live observation.
