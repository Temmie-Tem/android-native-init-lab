# WSTA186 Deep Propagation Replayable Live

Date: 2026-07-05 15:44 KST

## Verdict

WSTA186 fixes two live-execution correctness gaps found after the WSTA185
source gate:

- WSTA181 now propagates the WSTA179 deep audit evidence for WSTA175/WSTA170
  execution and WSTA167/WSTA170/WSTA175 pass decisions.
- WSTA178 now rebases the WSTA168 live command into the fresh WSTA178 run
  directory before emitting the WSTA177 execution packet, so repeated no-load
  live runs do not reuse the old WSTA167 run directory.

Result: PASS after the replayability fix.

## Source Changes

- Updated
  `workspace/public/src/scripts/server-distro/run_wsta178_seccomp_one_shot_execute_preflight.py`
  to emit a private rebased WSTA168 command packet under the WSTA178 run.
- Updated
  `workspace/public/src/scripts/server-distro/run_wsta181_seccomp_handoff_execute_audit_gate.py`
  to validate and propagate WSTA179 deep audit checks.
- Updated
  `workspace/public/src/scripts/server-distro/run_wsta185_seccomp_expiring_handoff_execute_gate.py`
  to require the propagated WSTA175/WSTA170/deep decision evidence.
- Updated focused tests for WSTA178, WSTA181, and WSTA185.

## Live Evidence

Initial propagation rerun exposed the replayability bug:

```text
workspace/private/runs/server-distro/wsta186-wsta185-deep-propagation-live-20260705T153800KST/
decision=wsta185-blocked-wsta181-returncode
root_cause=wsta167-runner-error ssh-keygen failed rc=1
```

The failure was host-side run-directory reuse.  The fixed WSTA178 preflight
then emitted:

```text
workspace/private/runs/server-distro/wsta186b-wsta178-one-shot-preflight-20260705T154219KST/
rebased_wsta168_command_valid=true
wsta167_run_dir=workspace/private/runs/server-distro/wsta186b-wsta178-one-shot-preflight-20260705T154219KST/rebased-wsta168-command/wsta167-live-run
```

Final WSTA185 live run:

```text
workspace/private/runs/server-distro/wsta186b-wsta185-deep-propagation-live-20260705T154252KST/
decision=wsta185-seccomp-expiring-handoff-execute-pass
```

Key results:

```text
execution_returncode_ok=true
wsta181_result_valid=true
wsta181_decision=wsta181-seccomp-handoff-execute-audit-pass
post_run_audit_decision=wsta179-seccomp-one-shot-result-audit-pass
wsta181_execute_command_executed=true
wsta178_execute_command_executed=true
wsta177_execute_command_executed=true
wsta175_execute_command_executed=true
wsta170_execute_command_executed=true
wsta167_decision_pass=true
wsta170_decision_pass=true
wsta175_decision_pass=true
```

Nested WSTA167 result:

```text
workspace/private/runs/server-distro/wsta186b-wsta178-one-shot-preflight-20260705T154219KST/rebased-wsta168-command/wsta167-live-run/wsta167_result.json
decision=wsta167-seccomp-live-observation-pass
observation_pass=true
chroot_cleanup_ok=true
final_selftest_fail_zero=true
work_image_restored_to_clean_hash_match=true
```

Post-run WSTA179 audit:

```text
workspace/private/runs/server-distro/wsta186b-wsta180-live-handoff-bundle-20260705T154228KST/post-run-wsta179-audit/wsta179_result.json
decision=wsta179-seccomp-one-shot-result-audit-pass
wsta177_result_valid=true
source_wsta175_executed=true
source_wsta170_executed=true
wsta167_decision_pass=true
```

## Safety Boundary

This unit did not flash, reboot, connect Wi-Fi, run DHCP, open a public tunnel,
mutate packet filters, write userdata, switch root, load a seccomp filter,
enforce seccomp, or supply the correct WSTA161 token.  The live portion only
ran the already-gated no-load chroot observation on the SD work image and
restored the work image to the clean hash.  Final native selftest after the
live run stayed `fail=0`.

## Validation

- `py_compile`:
  - `run_wsta178_seccomp_one_shot_execute_preflight.py`
  - `run_wsta181_seccomp_handoff_execute_audit_gate.py`
  - `run_wsta185_seccomp_expiring_handoff_execute_gate.py`
  - focused tests for WSTA178/WSTA181/WSTA185
- Focused WSTA178 + WSTA181 + WSTA185 tests: `12 tests OK`.
- Full server-distro regression: `643 tests OK`.
- Live WSTA185 deep-propagation replay: pass.
- Final device selftest: `fail=0`.

## Next

The WSTA execution path is now repeatable and carries deep execution evidence
to the top-level WSTA185 result.  The next useful unit is to collapse the
manual fresh sequence (WSTA177 source gate -> WSTA178 packet -> WSTA180 bundle
-> WSTA184 expiring handoff -> WSTA185 execute) into a single bounded fresh
orchestrator, so future attended no-load live observations do not require
manual path stitching.
