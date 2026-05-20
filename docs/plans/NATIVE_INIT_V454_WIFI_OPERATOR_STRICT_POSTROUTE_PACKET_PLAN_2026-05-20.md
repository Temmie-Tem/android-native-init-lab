# Native Init V454 Wi-Fi Operator Strict Post-route Packet Plan

Date: 2026-05-20

## Goal

V454 tightens V453 by ensuring post-route/proof command failures cannot be
silently ignored when the underlying V447 flow succeeds.  A successful preflight
or live flow must also leave V449/V450/V452 evidence behind.

## Scope

Allowed:

- generate private ignored host preflight and live scripts;
- run V446 secret guard and V447 plan before packet generation;
- validate generated scripts with shell syntax and fail-closed prompt probes;
- update V449/V450 routing to prefer the latest V448, V453, or V454 packet;
- require post-route command success when V447 succeeds.

Not allowed:

- read real Wi-Fi values during packet generation;
- run successful preflight/live paths during validation;
- boot/flash Android, enable Wi-Fi, scan, connect, or mutate the device during
  V454 generation;
- expose any server listener.

## Implementation

- Strict packet generator: `scripts/revalidation/wifi_operator_strict_postroute_packet_v454.py`
  - generates `run-v454-host-preflight-strict-route.sh`;
  - generates `run-v454-live-strict-proof.sh`;
  - both scripts run V449/V450/V452 after V447 attempts;
  - if V447 returns success but any post-route command fails, the script returns
    the post-route failure.
- Router updates:
  - `scripts/revalidation/wifi_handoff_result_router_v449.py`
  - `scripts/revalidation/wifi_operator_preflight_readiness_v450.py`

## Validation Plan

```text
python3 -m py_compile \
  scripts/revalidation/wifi_handoff_result_router_v449.py \
  scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  scripts/revalidation/wifi_operator_strict_postroute_packet_v454.py

python3 scripts/revalidation/wifi_operator_strict_postroute_packet_v454.py \
  --out-dir tmp/wifi/v454-operator-strict-postroute-packet-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_operator_strict_postroute_packet_v454.py \
  --out-dir tmp/wifi/v454-operator-strict-postroute-packet-run-<ts> \
  run

python3 scripts/revalidation/wifi_handoff_result_router_v449.py \
  --out-dir tmp/wifi/v449-wifi-handoff-result-router-v454-<ts> \
  run

python3 scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  --out-dir tmp/wifi/v450-operator-preflight-readiness-v454-<ts> \
  run

git diff --check
```

## Expected Decisions

- `v454-operator-strict-postroute-packet-plan-ready`
- `v454-operator-strict-postroute-secret-guard-blocked`
- `v454-operator-strict-postroute-v447-plan-blocked`
- `v454-operator-strict-postroute-validation-failed`
- `v454-operator-strict-postroute-packet-ready`

## Pass Criteria

V454 passes only when:

- V446 secret guard passes;
- V447 plan passes;
- strict post-route preflight/live scripts are generated privately under ignored
  `tmp/`;
- generated scripts pass `bash -n`;
- empty/cancel probes fail closed;
- V449 and V450 recommend the V454 host preflight script;
- no device command or Wi-Fi bring-up occurs.

## Next Gate

Run the V454 host preflight strict-route script.  If it passes, V449/V450 output
should route to the V454 live strict-proof script.  After live, V452 should
prove cleanup before stability or server policy work.

Server exposure remains blocked.
