# Native Init V500 Connect/DHCP/Ping Execution Plan

Date: 2026-05-21

## Goal

V500 is the first native-init gate that may advance from scan-only readiness to
a real Wi-Fi connection attempt, DHCP lease acquisition, and interface-bound
external ping.

The gate remains fail-closed. If the helper-side live executor is not present,
V500 must stop before any device mutation.

## Current Chain

```text
V497 scan-only pass
  -> V498 private native Wi-Fi target policy
  -> V499 connect-tool readiness
  -> V500 guarded native connect/DHCP/ping execution gate
  -> V501 helper v52 executor contract/deploy
  -> V502/V53 helper live executor implementation
```

V500 consumes existing readiness evidence instead of bypassing it:

- V497 decision must be `v497-native-scan-only-pass-redacted`;
- V498 decision must be `v498-native-private-policy-ready` or
  `v498-native-private-policy-ready-awaiting-v497`, with real non-placeholder
  env-derived private policy;
- V499 decision must be `v499-native-connect-ping-readiness-ready`;
- V500 live run must have exact approval and matching private env values.

## Implementation

New runner:

```text
scripts/revalidation/native_wifi_connect_ping_v500.py
```

Modes:

- `plan`: writes the execution plan only;
- `preflight`: runs the repository secret guard and classifies V497/V498/V499
  evidence;
- `run`: additionally requires exact live approval and validates
  `A90_WIFI_SSID`/`A90_WIFI_PSK` against the V498 private policy.

Exact live approval phrase:

```text
approve v500 native connect DHCP external ping only; cleanup required; no server exposure
```

## Fail-Closed Rule

V500 currently blocks on:

```text
wifi-active-session-connect-ping
```

That helper mode is scaffolded by V501 but still reports
`executor_implemented=0`. Therefore a V500 `run` can read approved private env
values and validate them, but it must not mutate the device until V502/V53 adds
the helper-side executor body.

The required V502/V53 executor must provide:

- temporary private supplicant config materialization;
- helper-owned bounded supplicant process;
- association wait on selected WLAN interface;
- DHCP client execution with explicit cleanup;
- interface-bound external ping to allowlisted IP targets;
- cleanup of supplicant, DHCP state, temporary secret files, and network state;
- redacted evidence only.

## Guardrails

- Raw SSID, BSSID, password, passphrase, or PSK must not be written to tracked
  files or evidence.
- V446 secret guard must pass before V500 proceeds.
- V500 `run` must not execute if V499 readiness is missing.
- No server listener exposure is allowed.
- External ping is allowed only after exact V500 approval.
- Any helper executor absence is a blocker, not a degraded pass.

## Validation

```text
python3 -m py_compile scripts/revalidation/native_wifi_connect_ping_v500.py

python3 scripts/revalidation/native_wifi_connect_ping_v500.py \
  --out-dir tmp/wifi/v500-native-connect-ping-plan-<ts> \
  plan

python3 scripts/revalidation/native_wifi_connect_ping_v500.py \
  --out-dir tmp/wifi/v500-native-connect-ping-preflight-<ts> \
  preflight

python3 scripts/revalidation/native_wifi_connect_ping_v500.py \
  --out-dir tmp/wifi/v500-native-connect-ping-run-refuse-<ts> \
  --allow-read-wifi-env --i-understand-wifi-secret-env \
  --allow-native-connect-dhcp-ping \
  --i-understand-native-wifi-connect-ping \
  --approval-phrase "approve v500 native connect DHCP external ping only; cleanup required; no server exposure" \
  run

python3 scripts/revalidation/wifi_private_secret_guard_v446.py --include-untracked run
git diff --check
```

Expected result before V501:

```text
decision: v500-native-connect-ping-blocked
reason includes: helper-live-executor
device_mutations: False
wifi_bringup_executed: False
external_ping_executed: False
```
