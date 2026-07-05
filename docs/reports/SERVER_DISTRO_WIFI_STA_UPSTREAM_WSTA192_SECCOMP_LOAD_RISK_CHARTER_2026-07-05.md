# WSTA192 Seccomp-Load Risk Charter

Date: 2026-07-05 16:34 KST

## Verdict

WSTA192 adds the host-only risk charter that separates any future real
seccomp-load/correct-token work from the now-closed WSTA187/WSTA190 no-load
workflow.  It consumes the WSTA190 live delegation pass and the WSTA164
load-env contract, then writes a non-executable charter for the next higher-risk
rungs.

Result: PASS.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta192_seccomp_load_risk_charter.py`.
- Added focused tests in
  `tests/test_server_distro_wsta192_seccomp_load_risk_charter.py`.

## Proof

Run:

```text
workspace/private/runs/server-distro/wsta192-seccomp-load-risk-charter-20260705T1640KST/
```

Decision:

```text
wsta192-seccomp-load-risk-charter-pass
```

Inputs:

```text
workspace/private/runs/server-distro/wsta190-wsta189-execute-gate-live-20260705T162249KST/wsta190_execute_gate.json
workspace/private/runs/server-distro/wsta164-seccomp-load-env-contract-chroot-proof-20260705T1329KST/wsta164_result.json
```

Generated charter artifacts:

```text
workspace/private/runs/server-distro/wsta192-seccomp-load-risk-charter-20260705T1640KST/wsta192_seccomp_load_risk_charter.json
workspace/private/runs/server-distro/wsta192-seccomp-load-risk-charter-20260705T1640KST/wsta192_seccomp_load_risk_charter.md
```

Charter state:

```text
READY_FOR_SEPARATE_SECCOMP_LOAD_DESIGN_NOT_EXECUTABLE
```

Key checks:

```text
wsta190_decision_live_pass=true
wsta190_top_no_mutation=true
wsta190_delegated_no_mutation=true
wsta164_decision_pass=true
wsta164_launcher_has_load_gate=true
wsta164_launcher_forwards_load_env=true
wsta164_safety_no_mutation=true
charter_state_not_executable=true
charter_guardrail_separate_script=true
charter_future_requires_correct_token_ack=true
```

## Safety Boundary

This proof did not flash, reboot, contact the device, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, switch root,
generate a live command, execute a live command, load a seccomp filter, enforce
seccomp, or supply the correct WSTA161 token.

The WSTA187/WSTA190 no-load path stays closed and must not be reused for real
seccomp-load behavior.  The charter requires a separate future chain:
WSTA193 host-only canary source proof, WSTA194 default-off operator packet,
WSTA195 read-only device readiness, and only then a separately attended
single-service canary load.

## Validation

- `py_compile`:
  - `run_wsta192_seccomp_load_risk_charter.py`
  - `test_server_distro_wsta192_seccomp_load_risk_charter.py`
- Focused WSTA192 tests: `7 tests OK`.
- Full server-distro regression: `678 tests OK`.
- WSTA192 proof run: pass.

## Next

Proceed to WSTA193 as a host-only source proof for the correct-token canary
shape.  It should still avoid live loading and should keep the real token out
of public artifacts.
