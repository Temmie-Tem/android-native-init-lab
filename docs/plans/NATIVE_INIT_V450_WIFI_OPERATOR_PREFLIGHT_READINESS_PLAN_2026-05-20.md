# Native Init V450 Wi-Fi Operator Preflight Readiness Plan

Date: 2026-05-20

## Goal

V450 audits the final operator handoff boundary before private Wi-Fi values are
entered locally.  It verifies that the generated V448 scripts are private,
contain the required prompt/cleanup markers, and that V449 still routes the
next safe action to host preflight.

## Scope

Allowed:

- read V448 packet, V449 router, V447 private preflight, and V447 live evidence;
- read generated V448 scripts for structural checks;
- check private file modes and prompt/cleanup/live-confirmation markers;
- recommend the next safe command.

Not allowed:

- read Wi-Fi secret env values;
- execute generated handoff scripts;
- run V443/V444/V445;
- boot/flash Android, enable Wi-Fi, scan, connect, or mutate the device;
- expose any server listener.

## Implementation

- Audit: `scripts/revalidation/wifi_operator_preflight_readiness_v450.py`
  - `plan`: records the audit plan;
  - `run`: checks latest V448/V449/V447 evidence and generated scripts;
  - emits host preflight, live, V449-route, or repair guidance depending on
    current evidence.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_operator_preflight_readiness_v450.py

python3 scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  --out-dir tmp/wifi/v450-operator-preflight-readiness-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  --out-dir tmp/wifi/v450-operator-preflight-readiness-run-<ts> \
  run

git diff --check
```

## Expected Decisions

- `v450-operator-preflight-readiness-plan-ready`
- `v450-operator-preflight-needs-v448-packet`
- `v450-operator-preflight-v448-not-ready`
- `v450-operator-preflight-script-audit-failed`
- `v450-operator-preflight-ready-run-host-preflight`
- `v450-operator-preflight-ready-for-live`
- `v450-operator-preflight-existing-preflight-blocked`
- `v450-operator-preflight-live-exists-route-v449`

## Pass Criteria

In the current pre-input state, V450 passes only if:

- latest V448 packet is ready;
- generated V448 host preflight and live scripts exist;
- scripts are private and contain prompt/cleanup markers;
- no private preflight or live result supersedes the packet;
- V449 still routes the next step to host preflight;
- no device command or Wi-Fi bring-up occurs.

## Next Gate

Run the recommended V448 host preflight script and enter Wi-Fi values locally.
After it completes, rerun V449 or V450 to route the next step.

Server exposure remains blocked.
