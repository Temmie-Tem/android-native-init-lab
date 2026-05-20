# Native Init V496 Scan-Only Contract Plan

- Date: 2026-05-21 KST
- Scope: host-side contract gate for native scan-only work after V495
- Status: implementation-ready; no live device command in V496
- Final Wi-Fi objective status: not achieved yet

## Purpose

V495 is still no-scan. If it proves that the helper-owned active session can
create a WLAN/wiphy/rfkill surface, the next safe step is not credentials or
external ping. The next step is a redacted scan-only proof.

V496 fixes the strategy before implementing that scan:

```text
V495 active session surface observed + cleanup clean
  -> V496 scan-only contract ready
  -> V497 integrated helper scan-only implementation
  -> V498 private credential materializer
  -> V499 native connect + DHCP + external ping
```

## Required V495 Evidence

V496 requires:

```text
decision=v495-native-active-session-surface-observed-cleaned
pass=true
active_session_started=true
surface_present_after_iwifi_start=true or surface_present_during=true
postflight.clean=true
surface_present_after_cleanup=false
wifi_bringup_executed=false
credentials_read=false
scan_connect_executed=false
external_ping_executed=false
```

Without this evidence, V496 remains blocked.

## Strategy Decision

V496 selects:

```text
execns-integrated-nl80211-scan
```

Reason:

- the scan must run while V495's private service-manager/HAL/CNSS/IWifi.start
  session is alive;
- the existing `a90_nl80211_ro` helper is read-only and cannot coordinate with
  that active-session lifetime;
- Android `cmd wifi start-scan` is a framework path, not the native-init proof
  chain;
- `wpa_supplicant` introduces association and credential state, so it belongs
  after the scan-only proof.

## Guardrails

V496 itself must not:

- execute device commands;
- start daemon/HAL/CNSS/supplicant;
- trigger scan/connect;
- read SSID/PSK env values;
- DHCP, route, or ping externally.

The later scan-only implementation must:

- run inside the helper-owned active session before cleanup;
- use an explicit approval phrase;
- report only bounded status and redacted counts;
- omit raw SSID, BSSID, password, passphrase, PSK, and scan-result details;
- avoid association, credentials, DHCP, routes, and external packet probes.

## Decision Rules

| decision | meaning |
|---|---|
| `v496-native-scan-only-contract-ready` | V495 proves active-session surface; implement integrated helper scan-only mode next |
| `v496-native-scan-only-contract-blocked` | V495 proof is missing, not passing, leaked surface, or already executed wider Wi-Fi actions |
| `v496-native-scan-only-contract-plan-ready` | plan-only; no evidence required |

## Next Work

1. Run V490 live policy-load proof after exact approval.
2. Run V491, V492, V493, V494, and V495 in order.
3. If V495 returns `surface-observed-cleaned`, run V496 preflight.
4. If V496 returns `contract-ready`, implement V497 helper mode
   `wifi-active-session-scan-only`.
