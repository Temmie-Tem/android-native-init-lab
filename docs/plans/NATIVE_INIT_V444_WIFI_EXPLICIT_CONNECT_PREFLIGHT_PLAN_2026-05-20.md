# Native Init V444 Wi-Fi Explicit Connect Preflight Plan

Date: 2026-05-20

## Goal

V444 is the final host-side safety gate before a bounded explicit Android
Wi-Fi scan/connect live run.

It consumes the private V442/V443 policy, reads local Wi-Fi env values only with
explicit approval, verifies that the SSID hash matches the allowlist, and emits
a sanitized command plan for V445.  It never executes ADB or device commands.

## Scope

Allowed:

- load V441 stability evidence;
- load private V442/V443 policy;
- read `A90_WIFI_SSID` and `A90_WIFI_PSK` only after explicit approval flags;
- verify SSID hash and credential presence/length;
- emit a sanitized V445 command plan using env placeholders.

Not allowed:

- ADB/device commands;
- device mutation;
- raw SSID/BSSID/password/passphrase/PSK in evidence;
- server exposure;
- external packet probes.

## Implementation

- Preflight: `scripts/revalidation/wifi_android_explicit_connect_preflight_v444.py`
  - auto-discovers latest materialized V443 private policy when available;
  - accepts explicit `--policy` path;
  - validates policy through V442's validator;
  - verifies env values against the allowlist without writing raw values;
  - produces V445 command templates:
    - enable Wi-Fi;
    - start scan;
    - list scan results with redaction;
    - connect with `cmd wifi connect-network`;
    - observe status/route/connectivity/listener surfaces;
    - cleanup by forgetting the resolved network and disabling Wi-Fi.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_android_explicit_connect_preflight_v444.py

python3 scripts/revalidation/wifi_android_explicit_connect_preflight_v444.py \
  --out-dir tmp/wifi/v444-explicit-connect-preflight-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_android_explicit_connect_preflight_v444.py \
  --out-dir tmp/wifi/v444-explicit-connect-preflight-missing-policy-<ts> \
  --allow-read-wifi-env --i-understand-wifi-secret-env \
  run

A90_WIFI_SSID='codex-test-network' A90_WIFI_PSK='12345678' \
python3 scripts/revalidation/wifi_android_explicit_connect_preflight_v444.py \
  --out-dir tmp/wifi/v444-explicit-connect-preflight-synthetic-pass-<ts> \
  --policy tmp/wifi/v444-synthetic-policy-<ts>.json \
  --allow-read-wifi-env --i-understand-wifi-secret-env \
  run

git diff --check
```

The missing-policy run must fail.  The synthetic run must pass and must not leak
the synthetic SSID or PSK into evidence.

## Expected Decisions

- `v444-wifi-explicit-connect-preflight-plan-ready`
- `v444-wifi-explicit-connect-preflight-ready`
- `v444-wifi-explicit-connect-preflight-missing-policy`
- `v444-wifi-explicit-connect-preflight-policy-invalid`
- `v444-wifi-explicit-connect-preflight-approval-required`
- `v444-wifi-explicit-connect-preflight-env-invalid`
- `v444-wifi-explicit-connect-preflight-v441-not-ready`

## Pass Criteria

A ready PASS must prove:

- V441 stable Wi-Fi exposure and cleanup evidence is ready;
- private policy passes V442 validation;
- approved env values match policy hash;
- credential env exists for `wpa2`/`wpa3`;
- no raw network identifier or credential is written to evidence;
- command plan keeps server exposure blocked and requires cleanup disable.

## Next Gate Rule

V445 may be the first bounded explicit scan/connect live run only after V444
returns:

```text
v444-wifi-explicit-connect-preflight-ready
```

V445 must still avoid server exposure and external packet probes.
