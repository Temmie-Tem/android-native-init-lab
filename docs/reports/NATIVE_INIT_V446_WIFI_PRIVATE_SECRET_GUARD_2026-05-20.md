# Native Init V446 Wi-Fi Private Secret Guard Report

Date: 2026-05-20

## Summary

V446 adds the missing repository-side safety gate for the private Wi-Fi
credential flow.  The current clean scan passes and confirms that no
repository-visible private policy or credential leak is present.

```text
decision: v446-wifi-private-secret-guard-pass
pass: True
reason: no repository-visible Wi-Fi private policy or credential leaks were found
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

## Implementation

- `.gitignore`
  - ignores local env files;
  - ignores private/local Wi-Fi target policy files;
  - keeps example env files trackable.
- `scripts/revalidation/wifi_private_secret_guard_v446.py`
  - verifies the required ignore patterns;
  - scans tracked files and included untracked files;
  - reports sanitized findings only;
  - detects private policy/env paths, non-placeholder Wi-Fi env assignments,
    raw connect commands, raw connected-SSID status, Wi-Fi-adjacent MAC values,
    and forbidden raw JSON policy fields.

## Validation

Static compile passed:

```text
python3 -m py_compile scripts/revalidation/wifi_private_secret_guard_v446.py
```

Clean scan passed:

```text
tmp/wifi/v446-wifi-private-secret-guard-postdoc-20260520-181446/
```

Negative probe passed in the expected fail-closed direction:

```text
decision: v446-wifi-private-secret-guard-findings
pass: False
findings: 3
```

Evidence:

```text
tmp/wifi/v446-wifi-private-secret-guard-negative-20260520-181251/
```

The synthetic probe file was removed after the negative validation.

## Interpretation

V445 live remains blocked by missing real private env/policy, but the repo now
has a pre-live guard that reduces the chance of committing Wi-Fi target
identifiers or credentials during the local materialization step.

## Next

Set private env values locally, run V443, rerun V444, then run V445 live.

Server exposure remains blocked.
