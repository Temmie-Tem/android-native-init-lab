# WSTA178 Seccomp One-Shot Execute Preflight

Date: 2026-07-05 14:49 KST

## Verdict

WSTA178 adds a host-only top-level execution preflight for WSTA177.  It consumes
the WSTA177 source-gate proof, revalidates the source-gate and WSTA168 command
artifact paths, then emits the exact WSTA177 one-shot execution command.  It
does not execute that command.

Result: PASS.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta178_seccomp_one_shot_execute_preflight.py`.
- Added focused tests in
  `tests/test_server_distro_wsta178_seccomp_one_shot_execute_preflight.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta178-seccomp-one-shot-execute-preflight-20260705T144926KST/
```

Decision:

```text
wsta178-seccomp-one-shot-execute-preflight-pass
```

Input source gate:

```text
workspace/private/runs/server-distro/wsta177-seccomp-one-shot-execute-gate-20260705T144329KST/wsta177_result.json
wsta177-blocked-explicit-execution-gate-required
```

Generated execution command:

```text
workspace/private/runs/server-distro/wsta178-seccomp-one-shot-execute-preflight-20260705T144926KST/wsta178_wsta177_execute_command.json
workspace/private/runs/server-distro/wsta178-seccomp-one-shot-execute-preflight-20260705T144926KST/wsta178_wsta177_execute_command.sh
```

Command state:

```text
state=READY_TO_RUN_NOT_EXECUTED
executed=false
required_ack_count=7
expected_decision=wsta177-seccomp-one-shot-execute-pass
expected_nested_wsta175_decision=wsta175-seccomp-handoff-execute-pass
expected_nested_wsta170_decision=wsta170-seccomp-live-observation-execute-pass
expected_nested_wsta167_decision=wsta167-seccomp-live-observation-pass
```

Checks:

```text
source_gate_valid=true
execution_command_valid=true
command_targets_wsta177=true
correct_token_literal_absent=true
no_external_network_inputs=true
```

Safety flags:

```text
wsta177_execute_command_generated=true
wsta177_execute_command_executed=false
wsta175_execute_command_executed=false
wsta170_execute_command_executed=false
live_command_executed=false
seccomp_filter_loaded=false
seccomp_enforced=false
correct_wsta161_token_supplied=false
```

## Execution Packet

The generated command targets WSTA177 and includes the full acknowledgement set:

```text
--prepare-wsta177-one-shot
--execute-wsta177-one-shot
--allow-wsta175-command-execution
--ack-fresh-preflight
--ack-no-correct-wsta161-token
--ack-no-seccomp-load
--ack-cleanup-required
```

Because WSTA177 performs WSTA176 immediately before execution, the lower-level
handoff is refreshed at execution time rather than reused from this WSTA178
preflight.

## Safety Boundary

This unit did not flash, reboot, connect Wi-Fi, run DHCP, open a public tunnel,
mutate packet filters, write userdata, switch root, execute WSTA177, execute
WSTA175, execute WSTA170, execute WSTA168/WSTA167, load a seccomp filter,
enforce seccomp, or supply the correct WSTA161 token.  WSTA178 itself was
host-only and did not contact the device; it only read the existing WSTA177
source-gate proof and WSTA168 command artifacts from private run storage.

## Validation

- `py_compile`:
  - `run_wsta178_seccomp_one_shot_execute_preflight.py`
  - `test_server_distro_wsta178_seccomp_one_shot_execute_preflight.py`
- Focused WSTA177 + WSTA178 tests: `8 tests OK`.
- WSTA178 preflight proof against the current WSTA177 source-gate artifact:
  pass.
- Full server-distro regression: `615 tests OK`.

## Next

The generated WSTA178 command packet is the clearest current operator-facing
surface for the no-load live observation.  Running it still requires explicit
operator approval, because it will execute WSTA177, which in turn executes
WSTA175/WSTA170/WSTA167 under the no-load seccomp observation path.
