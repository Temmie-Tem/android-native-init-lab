# v335 Wi-Fi Approval Gate Regression Report

- date: `2026-05-19`
- scope: host-only approval gate regression for V317/V320
- device command: none
- device mutation: none
- result: `PASS`

## Summary

v335 validates that partial approval combinations and V320-before-V317 are
refused without opening the live device path. The dangerous V317 full approval
combination is intentionally not executed and is protected by a hard refusal
guard in the regression runner.

## Evidence

- tool: `scripts/revalidation/wifi_approval_gate_regression.py`
- evidence: `tmp/wifi/v335-approval-gate-regression/`
- decision: `wifi-approval-gate-regression-pass`
- pass: `true`
- device commands executed: `false`
- device mutations: `false`
- dangerous V317 full approval case: `not run`

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_approval_gate_regression.py
python3 scripts/revalidation/wifi_approval_gate_regression.py \
  --out-dir tmp/wifi/v335-approval-gate-regression \
  run
git diff --check
```

Observed output:

```text
decision: wifi-approval-gate-regression-pass
pass: True
reason: all partial/blocked approval cases refused without device commands
```

## Interpretation

- V317 remains blocked unless the exact phrase and both mutation flags are
  supplied.
- V320 remains blocked even with its approval phrase while V317 PASS evidence is
  missing.
- No Wi-Fi daemon, scan, connect, or link-up path was exercised.
