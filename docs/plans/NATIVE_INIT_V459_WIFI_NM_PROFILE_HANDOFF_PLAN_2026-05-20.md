# Native Init V459 Wi-Fi NetworkManager Profile Handoff Plan

Date: 2026-05-20

## Goal

V459 reduces the remaining local Wi-Fi input blocker by generating a private
operator script that uses saved NetworkManager Wi-Fi profiles.  The operator
selects a profile by number; the script reads SSID/PSK locally through `nmcli`
and runs the strict V447 preflight/live handoff without printing profile names
or secret values.

## Scope

Allowed:

- run V446 repository-visible secret guard;
- run V447 `plan`;
- generate a private saved-profile operator script;
- validate generated script syntax and invalid-input fail-closed behavior;
- update V449/V450/V457/V458 to route to V459 as the newest handoff packet.

Not allowed during V459 generation:

- read Wi-Fi secret env values;
- execute a successful V447 preflight or live path;
- print saved profile names, SSIDs, or PSKs;
- boot/flash Android, enable Wi-Fi, scan, connect, or mutate the device;
- expose any server listener.

## Implementation

- Generator: `scripts/revalidation/wifi_operator_nm_profile_handoff_v459.py`
  - `plan`: records the saved-profile handoff plan;
  - `run`: runs V446 and V447 plan, writes
    `run-v459-nm-profile-wifi-flow.sh`, validates it with `bash -n`, and
    proves empty profile selection fails closed.
- Routing/readiness updates:
  - `scripts/revalidation/wifi_handoff_result_router_v449.py`
  - `scripts/revalidation/wifi_operator_preflight_readiness_v450.py`
  - `scripts/revalidation/wifi_operator_session_outcome_v457.py`
  - `scripts/revalidation/wifi_operator_session_bundle_v458.py`

## Validation Plan

```text
python3 -m py_compile \
  scripts/revalidation/wifi_handoff_result_router_v449.py \
  scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  scripts/revalidation/wifi_operator_nm_profile_handoff_v459.py \
  scripts/revalidation/wifi_operator_session_outcome_v457.py \
  scripts/revalidation/wifi_operator_session_bundle_v458.py

python3 scripts/revalidation/wifi_operator_nm_profile_handoff_v459.py \
  --out-dir tmp/wifi/v459-nm-profile-handoff-packet-run-<ts> \
  run

python3 scripts/revalidation/wifi_handoff_result_router_v449.py \
  --out-dir tmp/wifi/v449-wifi-handoff-result-router-v459-<ts> \
  run

python3 scripts/revalidation/wifi_operator_preflight_readiness_v450.py \
  --out-dir tmp/wifi/v450-operator-preflight-readiness-v459-<ts> \
  run

python3 scripts/revalidation/wifi_operator_session_outcome_v457.py \
  --out-dir tmp/wifi/v457-wifi-operator-session-outcome-v459-<ts> \
  run

python3 scripts/revalidation/wifi_operator_session_bundle_v458.py \
  --out-dir tmp/wifi/v458-wifi-operator-session-bundle-v459-<ts> \
  run

python3 scripts/revalidation/wifi_private_secret_guard_v446.py \
  --out-dir tmp/wifi/v446-wifi-private-secret-guard-v459-final-<ts> \
  --include-untracked \
  run

git diff --check
```

## Expected Decisions

- `v459-nm-profile-handoff-packet-plan-ready`
- `v459-nm-profile-handoff-secret-guard-blocked`
- `v459-nm-profile-handoff-v447-plan-blocked`
- `v459-nm-profile-handoff-packet-missing`
- `v459-nm-profile-handoff-marker-failed`
- `v459-nm-profile-handoff-validation-failed`
- `v459-nm-profile-handoff-packet-ready`

## Pass Criteria

V459 passes only when:

- V446 finds no repository-visible Wi-Fi secret material;
- V447 plan succeeds without live device mutation;
- generated script is private and contains NetworkManager/profile-selection,
  preflight/live, and route/proof markers;
- generated script passes shell syntax validation;
- empty profile selection exits before V447 success path;
- V449/V450/V457/V458 recommend the V459 script as the current next action.

## Next Gate

Run the generated V459 script locally.  Select the intended saved
NetworkManager Wi-Fi profile by number.  Type `V447-LIVE` only after preflight
passes and live execution is intentionally approved.
