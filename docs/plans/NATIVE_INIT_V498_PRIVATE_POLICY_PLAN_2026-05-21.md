# Native Init V498 Private Policy Plan

- Date: 2026-05-21 KST
- Scope: host-side private Wi-Fi target policy for later native-init connect
- Status: implemented as a non-device, secret-redacted materializer
- Final Wi-Fi objective status: not achieved yet

## Purpose

V497 proves only redacted scan. V498 prepares the private target policy required
for the eventual native-init connect/DHCP/external-ping proof without putting
SSID or PSK material into tracked files or shared evidence.

```text
V497 scan-only pass
  -> V498 private native target policy
  -> V499 bounded native connect + DHCP + external ping
```

V498 may be run before V497 is complete, but the result is only
`ready-awaiting-v497`. V499 must require both V497 scan-only pass evidence and
V498 private policy evidence.

## Policy Contract

Generated private policy:

- version: `v498`
- mode: `native-init-connect-allowlist`
- SSID source: `env:A90_WIFI_SSID`
- credential source for WPA2/WPA3: `env:A90_WIFI_PSK`
- stored identifier: SSID SHA-256 only
- stored credential: none
- persistent storage: false
- BSSID lock: false
- cleanup: `disconnect-and-stop-private-session`

The policy allows later V499 to attempt:

- native connect;
- DHCP;
- external ping to bounded allowlisted targets.

It does not itself execute any of those actions.

## Guardrails

V498 must not:

- execute device commands;
- mutate device state;
- trigger scan/connect/link-up;
- run DHCP, route traffic, or ping externally;
- write raw SSID, BSSID, password, passphrase, PSK, or PSK hash.

V498 may read `A90_WIFI_SSID` and `A90_WIFI_PSK` only when both explicit flags
are present:

```text
--allow-read-wifi-env --i-understand-wifi-secret-env
```

## Ignore/Leak Policy

Native private policy files are repository-ignored:

- `native-wifi-target-policy.private.json`
- `native-wifi-target-policy.local.json`
- `NATIVE_WIFI_TARGET_ALLOWLIST*.private.json`
- `NATIVE_WIFI_TARGET_ALLOWLIST*.local.json`

The V446 secret guard now also treats those paths as private if they appear in
tracked or untracked repository-visible locations.

## Decision Rules

| decision | meaning |
|---|---|
| `v498-native-private-policy-ready` | private policy is valid and V497 scan-only pass is already present |
| `v498-native-private-policy-ready-awaiting-v497` | private policy is valid but V497 scan-only pass is still required |
| `v498-native-private-policy-approval-required` | env read approval flags were not supplied |
| `v498-native-private-policy-env-missing` | required env values are absent or inconsistent |
| `v498-native-private-policy-validation-failed` | materialized policy violates native policy contract |
| `v498-native-private-policy-plan-ready` | plan-only; no env values read |

Only `v498-native-private-policy-ready` should unlock V499 live connect work.
