# Native Init V458 Wi-Fi Operator Session Bundle Plan

Date: 2026-05-20

## Goal

V458 creates a private, sanitized Wi-Fi operator session bundle after V456/V457.
It indexes current evidence and runs a no-secret leak audit so post-operator
results can be shared or reviewed without copying raw captures into the bundle.

## Scope

Allowed:

- read V456/V457/V447/V452 manifest evidence;
- write a private sanitized session index;
- scan referenced evidence files for obvious Wi-Fi secret leakage;
- summarize the current next gate.

Not allowed:

- read Wi-Fi secret env values;
- copy raw captures into the bundle;
- execute generated operator scripts;
- boot/flash Android, enable Wi-Fi, scan, connect, or mutate the device;
- expose any server listener.

## Implementation

- Bundle gate: `scripts/revalidation/wifi_operator_session_bundle_v458.py`
  - `plan`: records the bundle/leak-audit plan;
  - `run`: uses V457 classification, writes `session-index.json`,
    writes `leak-findings.json`, and emits a sanitized summary.

The bundle stores selected manifest metadata and referenced evidence paths.  It
does not duplicate raw command captures.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_operator_session_bundle_v458.py

python3 scripts/revalidation/wifi_operator_session_bundle_v458.py \
  --out-dir tmp/wifi/v458-wifi-operator-session-bundle-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_operator_session_bundle_v458.py \
  --out-dir tmp/wifi/v458-wifi-operator-session-bundle-run-<ts> \
  run

python3 scripts/revalidation/wifi_private_secret_guard_v446.py \
  --out-dir tmp/wifi/v446-wifi-private-secret-guard-v458-<ts> \
  --include-untracked \
  run

git diff --check
```

## Expected Decisions

- `v458-wifi-session-bundle-plan-ready`
- `v458-wifi-session-bundle-leak-audit-blocked`
- `v458-wifi-session-bundle-awaiting-operator`
- `v458-wifi-session-bundle-live-cleanup-pass`
- `v458-wifi-session-bundle-outcome-routed`

## Pass Criteria

V458 passes only when:

- the current V457 state can be summarized;
- no secret-like findings are detected in referenced Wi-Fi evidence;
- the bundle uses private EvidenceStore output;
- raw captures are not copied into the V458 bundle.

## Next Gate

Run the V456 one-session script locally.  After it exits, run V457 and V458 to
summarize the outcome and produce a shareable sanitized session index.
