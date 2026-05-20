# Native Init V444 Wi-Fi Explicit Connect Preflight Report

Date: 2026-05-20

## Summary

V444 added a host-side explicit scan/connect preflight.  The plan passed, the
missing-policy negative run failed safely, and a synthetic positive run passed
without leaking the synthetic SSID or PSK:

```text
decision: v444-wifi-explicit-connect-preflight-plan-ready
pass: True

decision: v444-wifi-explicit-connect-preflight-missing-policy
pass: False

decision: v444-wifi-explicit-connect-preflight-ready
pass: True
```

No device command ran.  No device state changed.

## Implementation

- `scripts/revalidation/wifi_android_explicit_connect_preflight_v444.py`
  - loads latest or explicit V441 evidence;
  - loads latest V443 materialized private policy or explicit `--policy`;
  - validates policy through V442;
  - reads Wi-Fi env values only with explicit approval flags;
  - verifies the SSID hash and credential readiness;
  - emits sanitized command templates for V445.

## Static Validation

```text
python3 -m py_compile scripts/revalidation/wifi_android_explicit_connect_preflight_v444.py

git diff --check
```

Both checks passed.

Evidence:

```text
tmp/wifi/v444-explicit-connect-preflight-plan-20260520-175411/
tmp/wifi/v444-explicit-connect-preflight-missing-policy-20260520-175411/
tmp/wifi/v444-explicit-connect-preflight-synthetic-pass-20260520-175411/
```

The synthetic positive run used local synthetic env values and confirmed that
those values were not written to evidence.

## Result

Current real state remains blocked:

```text
decision: v444-wifi-explicit-connect-preflight-missing-policy
reason: private Wi-Fi target policy is missing
next_gate: run V443 after setting private env values
```

Synthetic preflight proved the positive path:

```text
decision: v444-wifi-explicit-connect-preflight-ready
reason: private policy, env hashes, and command plan are ready for a bounded explicit scan/connect live gate
next_gate: V445 bounded explicit scan/connect live run; server exposure remains blocked
```

## Command Plan Contract

V445 must follow the sanitized plan:

- enable Android Wi-Fi;
- start scan;
- list scan results with SSID/BSSID redaction;
- connect using `cmd wifi connect-network` with env placeholders and autojoin
  disabled;
- observe Wi-Fi status, route, DNS, connectivity, and listener surfaces;
- cleanup by forgetting the resolved network and disabling Wi-Fi;
- restore native v319.

## Interpretation

V444 proves the explicit scan/connect runner can be gated before live device
actions.  Actual V445 remains blocked until V443 materializes a real private
policy from local env values.

## Next

Set local private env values, rerun V443, rerun V444 against the generated
private policy, then proceed to V445 bounded explicit scan/connect live run.

Server exposure remains blocked.
