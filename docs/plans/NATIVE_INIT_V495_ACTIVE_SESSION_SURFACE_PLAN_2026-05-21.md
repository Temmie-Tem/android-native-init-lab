# Native Init V495 Active-Session Surface Plan

- Date: 2026-05-21 KST
- Scope: bounded native active-session surface proof after V494 contract-ready
- Status: implementation-ready; live V495 requires successful V490..V494 evidence and exact approval
- Final Wi-Fi objective status: not achieved yet

## Purpose

V494 separates two states that must not be confused:

- `V493` can prove a transient WLAN/wiphy/rfkill surface while helper-owned
  daemons are running.
- `V493` also proves cleanup, so that transient surface is intentionally gone
  before any later V462 ping can run.

V495 introduces helper v49 mode:

```text
wifi-active-session-surface
```

This mode keeps the private service-manager, hwservicemanager, Wi-Fi HAL, CNSS,
and `IWifi.start()` surface alive for a bounded observation window, then cleans
up. It still does not scan, connect, read credentials, DHCP, route, or ping.

## Preconditions

V495 requires a V494 manifest:

```text
decision=v494-native-wifi-active-session-contract-ready
pass=true
wifi_bringup_executed=false
scan_connect_executed=false
external_ping_executed=false
```

The runner accepts this through:

```text
--v494-manifest path/to/V494/manifest.json
```

Without this evidence, V495 remains blocked.

## Helper v49 Contract

The helper must expose:

```text
a90_android_execns_probe v49
--mode wifi-active-session-surface
--allow-iwifi-start-only
wifi_active_session.begin=1
wifi_active_session.cleanup_attempted=1
```

The active-session mode:

- starts only private service-manager/hwservicemanager/HAL/CNSS children
- calls `IWifi.start()` once only if `IWifi/default` is non-null
- observes `wlan*`, `phy*`, `/proc/net/wireless`, and Wi-Fi rfkill surfaces
- keeps the session alive only until the bounded timeout
- terminates and reaps all helper-owned children before returning

## Approval

Deploy approval phrase:

```text
approve v495 deploy execns helper v49 only; no daemon start and no Wi-Fi bring-up
```

Live proof approval phrase:

```text
approve v495 native active-session surface proof only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Decision Rules

| decision | meaning |
|---|---|
| `v495-native-active-session-surface-observed-cleaned` | active session created a surface and cleanup was clean; proceed to V496 scan-only |
| `v495-native-active-session-no-surface-delta` | `IWifi.start()` returned but no WLAN surface appeared |
| `v495-native-active-session-transaction-failed` | `IWifi.start()` transaction executed but did not return cleanly |
| `v495-native-active-session-service-null` | `IWifi/default` handle was not returned |
| `v495-native-active-session-surface-leaked` | WLAN surface remained after cleanup; inspect device before continuing |
| `v495-native-active-session-blocked` | helper, runtime, V494, process, or Wi-Fi-clean precondition missing |

## Next Work

1. Deploy helper v49 only after explicit deploy approval.
2. Run V490 live policy-load proof after exact V490 approval.
3. Run V491, V492, V493, then V494.
4. Run V495 live proof if V494 returns `contract-ready`.
5. If V495 returns `surface-observed-cleaned`, implement V496 native scan-only proof.
