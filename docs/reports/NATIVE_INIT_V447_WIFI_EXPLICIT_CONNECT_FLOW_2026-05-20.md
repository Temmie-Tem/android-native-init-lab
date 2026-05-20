# Native Init V447 Wi-Fi Explicit Connect Flow Report

Date: 2026-05-20

## Summary

V447 adds a one-command gated flow for the private Wi-Fi credential path:

```text
V446 secret guard → V443 private policy → V444 preflight → optional V445 live
```

The current real environment is still blocked because private Wi-Fi env values
are absent.  That block occurs before any device command or Wi-Fi bring-up.

```text
decision: v447-explicit-connect-flow-v443-blocked
pass: False
reason: required Wi-Fi env values are missing or inconsistent
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

## Implementation

- `scripts/revalidation/wifi_explicit_connect_flow_v447.py`
  - runs V446 before materialization;
  - runs V443 only after env-read approval flags;
  - runs V444 against the materialized or supplied private policy;
  - runs V445 only when `--allow-live-v445` and the V445 live approval flags
    are present;
  - redacts env values from nested transcripts.

## Validation

Static compile passed:

```text
python3 -m py_compile scripts/revalidation/wifi_explicit_connect_flow_v447.py
```

Plan evidence:

```text
tmp/wifi/v447-explicit-connect-flow-plan-final2-20260520-182148/
```

Current real env-missing block:

```text
tmp/wifi/v447-explicit-connect-flow-env-missing-final2-20260520-182148/
```

Synthetic host-only positive path:

```text
decision: v447-explicit-connect-flow-preflight-ready
pass: True
reason: V446/V443/V444 passed; V445 live was not requested
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Evidence:

```text
tmp/wifi/v447-explicit-connect-flow-synthetic-final2-20260520-182148/
```

Synthetic leak scan over the V447 evidence was clean.

## Interpretation

The remaining blocker is not tooling order anymore.  The next required input is
local private env values.  Once they are set, V447 can prove V446/V443/V444 in
one command and then optionally execute V445 live with explicit live flags.

## Next

Set private local env values outside chat/tracked files, run V447 host
preflight, then rerun V447 with live flags for the bounded V445 explicit
scan/connect test.

Server exposure remains blocked.
