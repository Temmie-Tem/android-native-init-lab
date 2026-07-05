# WSTA180 Seccomp Live Handoff Bundle

Date: 2026-07-05 14:59 KST

## Verdict

WSTA180 adds a host-only operator handoff bundle for the no-load live
observation.  It packages the WSTA178 execution packet and the WSTA179 post-run
audit command into one audited artifact.  It does not execute WSTA177 or the
WSTA178 command packet.

Result: PASS.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta180_seccomp_live_handoff_bundle.py`.
- Added focused tests in
  `tests/test_server_distro_wsta180_seccomp_live_handoff_bundle.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta180-seccomp-live-handoff-bundle-20260705T145906KST/
```

Decision:

```text
wsta180-seccomp-live-handoff-bundle-pass
```

Input WSTA178 execution packet:

```text
workspace/private/runs/server-distro/wsta178-seccomp-one-shot-execute-preflight-20260705T144926KST/wsta178_wsta177_execute_command.json
workspace/private/runs/server-distro/wsta178-seccomp-one-shot-execute-preflight-20260705T144926KST/wsta178_wsta177_execute_command.sh
```

Generated handoff bundle:

```text
workspace/private/runs/server-distro/wsta180-seccomp-live-handoff-bundle-20260705T145906KST/wsta180_operator_handoff.json
workspace/private/runs/server-distro/wsta180-seccomp-live-handoff-bundle-20260705T145906KST/wsta180_operator_handoff_commands.sh
```

Bundle state:

```text
state=READY_FOR_OPERATOR_APPROVAL_NOT_EXECUTED
execute_packet_script=workspace/private/runs/server-distro/wsta178-seccomp-one-shot-execute-preflight-20260705T144926KST/wsta178_wsta177_execute_command.sh
expected_wsta177_result_json=workspace/private/runs/server-distro/wsta178-seccomp-one-shot-execute-preflight-20260705T144926KST/wsta177-live-run/wsta177_result.json
post_run_audit_command_len=13
```

Pre-run WSTA179 audit:

```text
workspace/private/runs/server-distro/wsta180-seccomp-live-handoff-bundle-20260705T145906KST/pre-run-wsta179-result-audit/wsta179_result.json
wsta179-blocked-wsta177-result-missing
```

This missing-result decision is expected before WSTA177 is executed.

## Checks

```text
pre_run_audit_missing_result=true
pre_run_command_packet_valid=true
pre_run_no_live_execution=true
execution_packet_valid=true
post_run_audit_command_valid=true
bundle_valid=true
execute_targets_wsta177=true
post_audit_targets_wsta179=true
correct_token_literal_absent=true
no_external_network_inputs=true
```

## Safety Boundary

This unit did not flash, reboot, connect Wi-Fi, run DHCP, open a public tunnel,
mutate packet filters, write userdata, switch root, execute WSTA177, execute
WSTA175, execute WSTA170, execute WSTA168/WSTA167, load a seccomp filter,
enforce seccomp, or supply the correct WSTA161 token.  WSTA180 only generated a
private operator handoff bundle.

## Validation

- `py_compile`:
  - `run_wsta180_seccomp_live_handoff_bundle.py`
  - `test_server_distro_wsta180_seccomp_live_handoff_bundle.py`
- Focused WSTA179 + WSTA180 tests: `8 tests OK`.
- WSTA180 handoff-bundle proof against the current WSTA178 command packet:
  pass.
- Full server-distro regression: `623 tests OK`.

## Next

The live no-load observation is now packaged as an operator handoff.  It still
requires explicit approval to run the WSTA178 execution script, then the
post-run WSTA179 audit command should be run against the resulting WSTA177
result JSON.
