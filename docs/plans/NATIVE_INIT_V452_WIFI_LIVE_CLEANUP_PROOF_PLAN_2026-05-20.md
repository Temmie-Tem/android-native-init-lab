# Native Init V452 Wi-Fi Live Cleanup Proof Plan

Date: 2026-05-20

## Goal

V452 adds the post-live evidence gate for explicit Wi-Fi connect.  Once V447
live runs, the next work must not proceed to stability or server policy unless
cleanup containment and native rollback evidence are proven from V447/V445
manifests.

## Scope

Allowed:

- read V447 live and nested V445 manifests;
- verify live pass, V445 cleanup pass, cleanup state, connection observation,
  forget-network cleanup, exposure removal, and rollback step presence;
- produce a pass/block/awaiting-live decision.

Not allowed:

- read Wi-Fi secret env values;
- execute cleanup, handoff, or device commands;
- mutate Android/native state;
- expose any server listener.

## Implementation

- Gate: `scripts/revalidation/wifi_live_cleanup_proof_v452.py`
  - `plan`: records cleanup proof plan;
  - `run`: classifies current live evidence;
  - `--live-manifest`: allows synthetic or explicit manifest validation.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_live_cleanup_proof_v452.py

python3 scripts/revalidation/wifi_live_cleanup_proof_v452.py \
  --out-dir tmp/wifi/v452-wifi-live-cleanup-proof-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_live_cleanup_proof_v452.py \
  --out-dir tmp/wifi/v452-wifi-live-cleanup-proof-run-<ts> \
  run

python3 scripts/revalidation/wifi_live_cleanup_proof_v452.py \
  --out-dir tmp/wifi/v452-wifi-live-cleanup-proof-synth-pass-<ts> \
  --live-manifest tmp/wifi/v452-synthetic-validation-<ts>/live-pass.json \
  run

python3 scripts/revalidation/wifi_live_cleanup_proof_v452.py \
  --out-dir tmp/wifi/v452-wifi-live-cleanup-proof-synth-block-<ts> \
  --live-manifest tmp/wifi/v452-synthetic-validation-<ts>/live-blocked.json \
  run

git diff --check
```

The synthetic blocked cleanup run must fail closed.

## Expected Decisions

- `v452-wifi-live-cleanup-proof-plan-ready`
- `v452-wifi-live-cleanup-proof-awaiting-live`
- `v452-wifi-live-cleanup-proof-pass`
- `v452-wifi-live-cleanup-proof-blocked`

## Pass Criteria

Post-live V452 passes only when:

- latest V447 live decision is pass;
- nested V445 decision is cleanup pass;
- Wi-Fi connection was observed;
- resolved network forget passed;
- cleanup state proves disabled status and no `wlan0` IP, route, DNS,
  validated Wi-Fi connectivity, or global listener exposure;
- exposure removal is true;
- restore-native step is present;
- no V452 device command or Wi-Fi bring-up occurs.

## Next Gate

Current state is expected to be awaiting live.  After V447 live runs, V452 must
pass before Wi-Fi stability or server binding policy work proceeds.

Server exposure remains blocked.
