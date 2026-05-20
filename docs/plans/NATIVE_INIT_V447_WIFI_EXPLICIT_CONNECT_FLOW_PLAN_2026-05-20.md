# Native Init V447 Wi-Fi Explicit Connect Flow Plan

Date: 2026-05-20

## Goal

V447 turns the V446/V443/V444/V445 pieces into one gated operator flow.  The
goal is to reduce manual sequencing risk before the first real explicit
Android Wi-Fi scan/connect live run.

## Scope

Allowed:

- run V446 repository secret guard first;
- materialize the ignored private policy with V443;
- validate the private policy and local env with V444;
- optionally hand off to V445 live only with explicit live flags;
- redact nested step transcripts before writing evidence.

Not allowed:

- run V445 live before V446, V443, and V444 pass;
- print raw Wi-Fi env values in command transcripts;
- enable Wi-Fi, scan, connect, boot/flash Android, or mutate the device unless
  live mode is explicitly requested and approved;
- expose any server listener.

## Implementation

- Runner: `scripts/revalidation/wifi_explicit_connect_flow_v447.py`
  - `plan`: records the flow plan without mutation;
  - `run`: executes V446 → V443 → V444;
  - optional live mode executes V445 after V444 passes;
  - records nested manifests and sanitized step transcripts.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_explicit_connect_flow_v447.py

python3 scripts/revalidation/wifi_explicit_connect_flow_v447.py \
  --out-dir tmp/wifi/v447-explicit-connect-flow-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_explicit_connect_flow_v447.py \
  --out-dir tmp/wifi/v447-explicit-connect-flow-env-missing-<ts> \
  --allow-read-wifi-env --i-understand-wifi-secret-env \
  run

A90_WIFI_SSID='<synthetic>' A90_WIFI_PSK='<synthetic>' \
python3 scripts/revalidation/wifi_explicit_connect_flow_v447.py \
  --out-dir tmp/wifi/v447-explicit-connect-flow-synthetic-preflight-<ts> \
  --allow-read-wifi-env --i-understand-wifi-secret-env \
  run

git diff --check
```

The synthetic positive path must stop at V444 preflight unless
`--allow-live-v445` and all V445 live approval flags are present.

## Expected Decisions

- `v447-explicit-connect-flow-plan-ready`
- `v447-explicit-connect-flow-secret-guard-blocked`
- `v447-explicit-connect-flow-v443-blocked`
- `v447-explicit-connect-flow-preflight-blocked`
- `v447-explicit-connect-flow-preflight-ready`
- `v447-explicit-connect-flow-live-approval-required`
- `v447-explicit-connect-flow-live-pass`
- `v447-explicit-connect-flow-live-failed`

## Pass Criteria

V447 host preflight passes only when:

- V446 returns clean;
- V443 materializes a private policy without raw secret evidence;
- V444 returns ready for that policy/env pair;
- V445 live is not run unless explicitly requested.

V447 live passes only when the nested V445 live manifest passes.

## Next Gate

Use V447 after setting local private env values.  With real env values present,
run host preflight first.  If it passes, rerun with live approval flags for the
bounded V445 explicit scan/connect test.

Server exposure remains blocked.
