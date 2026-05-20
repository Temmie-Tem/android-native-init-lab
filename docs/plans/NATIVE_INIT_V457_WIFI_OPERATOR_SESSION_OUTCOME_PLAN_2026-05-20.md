# Native Init V457 Wi-Fi Operator Session Outcome Plan

Date: 2026-05-20

## Goal

V457 adds a no-secret outcome gate for the V456 one-session Wi-Fi handoff.  It
lets the repo classify the current state before or after operator execution
without reading Wi-Fi credentials or running generated handoff scripts.

## Scope

Allowed:

- read V456 packet evidence;
- read latest real V447 private preflight evidence;
- read latest real V447/V445 live evidence;
- read V452 cleanup-proof evidence;
- summarize the next safe action from those manifests.

Not allowed:

- read Wi-Fi secret env values;
- execute generated operator scripts;
- boot/flash Android, enable Wi-Fi, scan, connect, or mutate the device;
- expose any server listener.

## Implementation

- Outcome gate: `scripts/revalidation/wifi_operator_session_outcome_v457.py`
  - `plan`: records the outcome gate plan;
  - `run`: classifies the latest V456/V447/V452 evidence state and writes an
    ignored `tmp/` manifest/summary.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_operator_session_outcome_v457.py

python3 scripts/revalidation/wifi_operator_session_outcome_v457.py \
  --out-dir tmp/wifi/v457-wifi-operator-session-outcome-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_operator_session_outcome_v457.py \
  --out-dir tmp/wifi/v457-wifi-operator-session-outcome-run-<ts> \
  run

python3 scripts/revalidation/wifi_private_secret_guard_v446.py \
  --out-dir tmp/wifi/v446-wifi-private-secret-guard-v457-<ts> \
  --include-untracked \
  run

git diff --check
```

## Expected Decisions

- `v457-wifi-operator-session-outcome-plan-ready`
- `v457-wifi-session-needs-v456-packet`
- `v457-wifi-session-v456-not-ready`
- `v457-wifi-session-awaiting-operator`
- `v457-wifi-session-preflight-blocked`
- `v457-wifi-session-preflight-pass-live-pending`
- `v457-wifi-session-live-blocked`
- `v457-wifi-session-cleanup-proof-pending`
- `v457-wifi-session-live-cleanup-pass`

## Pass Criteria

V457 passes when it can classify the current session state without secrets or
device mutation.  Pre-operator state should pass as
`v457-wifi-session-awaiting-operator`; post-live work should proceed only after
`v457-wifi-session-live-cleanup-pass`.

## Next Gate

Run the generated V456 one-session script locally.  After it exits, run V457 to
summarize whether the session is blocked, ready for live, awaiting cleanup proof,
or ready for bounded Wi-Fi stability/server-binding policy.
