# Native Init V456 Wi-Fi Operator One-session Packet Plan

Date: 2026-05-20

## Goal

V456 reduces the remaining Wi-Fi handoff friction by generating one private
operator script that prompts for Wi-Fi values once, runs V447 host preflight,
routes/proves the result, and then optionally runs V447 live in the same shell
session.

## Scope

Allowed:

- run V446 repository-visible secret guard;
- run V447 `plan`;
- generate an ignored, private one-session operator script;
- validate generated script syntax and empty-input fail-closed behavior;
- update V449/V450 to recognize V456 as the newest handoff packet.

Not allowed during V456 generation:

- read Wi-Fi secret env values;
- execute a successful V447 preflight or live path;
- boot/flash Android, enable Wi-Fi, scan, connect, or mutate the device;
- expose any server listener.

## Implementation

- Generator: `scripts/revalidation/wifi_operator_one_session_packet_v456.py`
  - `plan`: records the one-session handoff plan;
  - `run`: runs V446 and V447 plan, writes `run-v456-one-session-wifi-flow.sh`,
    validates it with `bash -n`, and proves empty Wi-Fi input fails closed.
- Router/readiness updates:
  - `scripts/revalidation/wifi_handoff_result_router_v449.py`
  - `scripts/revalidation/wifi_operator_preflight_readiness_v450.py`

The generated script keeps Wi-Fi values as shell-local variables and passes
them only to V447 child processes with `env "A90_WIFI_..."`.  V449/V450/V452
route/proof commands do not need Wi-Fi secrets and should not inherit them.

## Validation Plan

```text
python3 -m py_compile \
  scripts/revalidation/wifi_handoff_result_router_v449.py \
  scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  scripts/revalidation/wifi_operator_one_session_packet_v456.py

python3 scripts/revalidation/wifi_operator_one_session_packet_v456.py \
  --out-dir tmp/wifi/v456-operator-one-session-packet-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_operator_one_session_packet_v456.py \
  --out-dir tmp/wifi/v456-operator-one-session-packet-run-<ts> \
  run

python3 scripts/revalidation/wifi_handoff_result_router_v449.py \
  --out-dir tmp/wifi/v449-wifi-handoff-result-router-v456-<ts> \
  run

python3 scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  --out-dir tmp/wifi/v450-operator-preflight-readiness-v456-<ts> \
  run

python3 scripts/revalidation/wifi_private_secret_guard_v446.py \
  --out-dir tmp/wifi/v446-wifi-private-secret-guard-v456-<ts> \
  --include-untracked \
  run

git diff --check
```

## Expected Decisions

- `v456-operator-one-session-packet-plan-ready`
- `v456-operator-one-session-secret-guard-blocked`
- `v456-operator-one-session-v447-plan-blocked`
- `v456-operator-one-session-packet-missing`
- `v456-operator-one-session-marker-failed`
- `v456-operator-one-session-validation-failed`
- `v456-operator-one-session-packet-ready`

## Pass Criteria

V456 passes only when:

- V446 finds no repository-visible Wi-Fi secret material;
- V447 plan succeeds without live device mutation;
- generated one-session script is private and contains preflight/live/proof
  markers;
- generated script passes shell syntax validation;
- empty Wi-Fi input exits before V447 success path;
- V449 and V450 recommend the V456 one-session script as the next action.

## Next Gate

Run the generated V456 one-session script, enter Wi-Fi values locally, and type
`V447-LIVE` only after preflight passes and live execution is intentionally
approved.  Server exposure remains blocked.
