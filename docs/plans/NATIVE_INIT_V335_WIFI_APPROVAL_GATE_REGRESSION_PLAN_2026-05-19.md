# v335 Plan: Wi-Fi Approval Gate Regression

- date: `2026-05-19`
- scope: host-only approval gate regression for V317/V320
- boot image change: none planned
- device mutation: none planned
- status: implemented / validated

## Summary

The next live step is blocked on the exact V317 approval phrase. Before running
any approved live proof, the approval gates should be regression-tested so
partial approval cannot accidentally execute bridge/device commands.

v335 adds a host-only regression runner for safe refusal cases.

## Cases

- V317 `run` with no approval.
- V317 `run` with phrase only.
- V317 `run` with flags only.
- V317 `cleanup` with no approval.
- V320 `run` with no approval.
- V320 `run` with full V320 approval flags while V317 PASS evidence is still
  missing.

The dangerous V317 full approval combination is explicitly not run by this
regression, and the runner has a hard refusal guard for that exact combination.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_approval_gate_regression.py
python3 scripts/revalidation/wifi_approval_gate_regression.py \
  --out-dir tmp/wifi/v335-approval-gate-regression \
  run
git diff --check
```

Expected result:

```text
decision: wifi-approval-gate-regression-pass
pass: True
```

## Acceptance

- All safe refusal cases pass.
- No device command is executed.
- No device mutation is performed.
- V317 full approval live path remains unexecuted until explicit operator phrase.
