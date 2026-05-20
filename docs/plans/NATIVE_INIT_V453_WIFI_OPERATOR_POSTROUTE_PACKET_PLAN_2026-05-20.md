# Native Init V453 Wi-Fi Operator Post-route Packet Plan

Date: 2026-05-20

## Goal

V453 removes the remaining manual post-run routing step from the operator Wi-Fi
handoff.  The generated scripts should run V447 preflight/live and then
automatically run V449/V450/V452 so the next state is recorded immediately.

## Scope

Allowed:

- generate private ignored host preflight and live scripts;
- run V446 secret guard and V447 plan before packet generation;
- validate generated scripts with shell syntax and fail-closed prompt probes;
- update V449/V450 routing to prefer the latest V448 or V453 packet;
- include post-route commands after V447 preflight/live attempts.

Not allowed:

- read real Wi-Fi values during packet generation;
- run successful preflight/live paths during validation;
- boot/flash Android, enable Wi-Fi, scan, connect, or mutate the device during
  V453 generation;
- expose any server listener.

## Implementation

- Packet generator: `scripts/revalidation/wifi_operator_postroute_packet_v453.py`
  - `plan`: records the post-route packet plan;
  - `run`: runs V446, runs V447 plan, writes private scripts, and validates
    them with `bash -n` plus fail-closed probes.
- Router updates:
  - `scripts/revalidation/wifi_handoff_result_router_v449.py`
  - `scripts/revalidation/wifi_operator_preflight_readiness_v450.py`

## Validation Plan

```text
python3 -m py_compile \
  scripts/revalidation/wifi_handoff_result_router_v449.py \
  scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  scripts/revalidation/wifi_operator_postroute_packet_v453.py

python3 scripts/revalidation/wifi_operator_postroute_packet_v453.py \
  --out-dir tmp/wifi/v453-operator-postroute-packet-plan-final-<ts> \
  plan

python3 scripts/revalidation/wifi_operator_postroute_packet_v453.py \
  --out-dir tmp/wifi/v453-operator-postroute-packet-run-final-<ts> \
  run

python3 scripts/revalidation/wifi_handoff_result_router_v449.py \
  --out-dir tmp/wifi/v449-wifi-handoff-result-router-v453-final-<ts> \
  run

python3 scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  --out-dir tmp/wifi/v450-operator-preflight-readiness-v453-final-<ts> \
  run

git diff --check
```

## Expected Decisions

- `v453-operator-postroute-packet-plan-ready`
- `v453-operator-postroute-secret-guard-blocked`
- `v453-operator-postroute-v447-plan-blocked`
- `v453-operator-postroute-validation-failed`
- `v453-operator-postroute-packet-ready`

## Pass Criteria

V453 passes only when:

- V446 secret guard passes;
- V447 plan passes;
- post-route preflight/live scripts are generated privately under ignored
  `tmp/`;
- generated scripts pass `bash -n`;
- empty/cancel probes fail closed;
- V449 and V450 recommend the new V453 host preflight script;
- no device command or Wi-Fi bring-up occurs.

## Next Gate

Run the V453 host preflight-and-route script.  If it passes, V449/V450 output
should route to the V453 live-and-proof script.  After live, V452 should record
cleanup proof.

Server exposure remains blocked.
