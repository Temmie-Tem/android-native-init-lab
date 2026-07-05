# WSTA196 Seccomp-Load Canary Source Gate

Date: 2026-07-05 17:05 KST

## Verdict

WSTA196 adds the attended seccomp-load canary runner source.  The runner has a
host-only source-gate mode that validates WSTA195 readiness plus the WSTA194
private/default-off operator packet, and it has a separately gated execution
mode for a future attended live attempt.

Result: PASS for source-gate mode.  Live execute was not run.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta196_seccomp_load_canary_execute.py`.
- Added focused tests in
  `tests/test_server_distro_wsta196_seccomp_load_canary_execute.py`.

## Proof

Run:

```text
workspace/private/runs/server-distro/wsta196-seccomp-load-canary-source-gate-20260705T170553KST/
```

Decision:

```text
wsta196-seccomp-load-canary-source-gate-pass
```

Inputs:

```text
workspace/private/runs/server-distro/wsta195-seccomp-load-canary-readiness-20260705T165710KST/wsta195_seccomp_load_canary_readiness.json
workspace/private/runs/server-distro/wsta194-seccomp-load-canary-operator-packet-20260705T1648KST/wsta194_seccomp_load_canary_operator_packet.json
```

Generated private artifacts:

```text
workspace/private/runs/server-distro/wsta196-seccomp-load-canary-source-gate-20260705T170553KST/wsta196_result.json
workspace/private/runs/server-distro/wsta196-seccomp-load-canary-source-gate-20260705T170553KST/wsta196_seccomp_load_canary_source_gate.json
workspace/private/runs/server-distro/wsta196-seccomp-load-canary-source-gate-20260705T170553KST/wsta196_seccomp_load_canary_source_gate.md
```

Source-gate state:

```text
LIVE_RUNNER_SOURCE_READY_DEFAULT_OFF_NOT_EXECUTED
```

Canary shape:

```text
canary_service=dpublic-hud
policy_service=dpublic-hud-intent
private_token_env=A90_PRIVATE_WSTA161_LOAD_TOKEN
ready_for_attended_execution=true
ready_for_unattended_execution=false
single_service_canary=true
live_command_executed=false
correct_wsta161_token_supplied=false
seccomp_filter_loaded=false
seccomp_enforced=false
```

Key checks:

```text
wsta195_readiness_valid=true
wsta194_packet_valid=true
source_gate_valid=true
fresh_health_required=true
post_health_required=true
execute_flags_complete=true
launcher_command_single_service_hud=true
launcher_command_canary_true=true
token_literal_absent=true
no_external_network_inputs=true
```

## Execution Path

The WSTA196 runner includes a future attended execution path, but it remains
closed unless all of these are true:

```text
--execute-real-seccomp-load-canary
--allow-correct-wsta161-token
--ack-seccomp-load-risk
--ack-single-service-canary-only
--ack-no-flash-no-reboot
--ack-cleanup-required
A90_PRIVATE_WSTA161_LOAD_TOKEN is present and matches the WSTA161 helper token
fresh read-only native health passes before execution
post-run read-only native health passes after execution
```

Focused tests mock the device health and canary command hooks to prove the
execution path ordering and marker validation.  The source-gate proof did not
use those live hooks.

## Safety Boundary

This proof did not flash, reboot, contact the device, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, switch root,
execute an operator packet, generate or execute a live command, supply the
correct WSTA161 token, load a seccomp filter, or enforce seccomp.

The runner source keeps the token value out of new public artifacts; the
execution mode reads it only from the private operator environment.

## Validation

- `py_compile`:
  - `run_wsta196_seccomp_load_canary_execute.py`
  - `test_server_distro_wsta196_seccomp_load_canary_execute.py`
- Focused WSTA196 tests: `6 tests OK`.
- Full server-distro regression: `708 tests OK`.
- WSTA196 source-gate proof run: pass.

## Next

Proceed to WSTA197: perform the live-readiness/transport decision for the
attended WSTA196 execution path, then run only if the operator supplies the
private token and fresh native health checks pass.
