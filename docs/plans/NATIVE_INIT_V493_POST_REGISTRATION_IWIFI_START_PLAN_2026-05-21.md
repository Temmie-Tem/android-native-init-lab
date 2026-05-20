# Native Init V493 Post-Registration IWifi.start Plan

- Date: 2026-05-21 KST
- Scope: no-credential `IWifi.start()` surface proof after Samsung registration appears
- Status: implementation-ready; live V493 requires a successful V492 registration-present manifest
- Final Wi-Fi objective status: not achieved yet

## Background

V492 is designed to retry Samsung `ISehWifi/default` registration after SELinux policy load and HAL-domain handoff. If that registration appears, the next useful gate is not full Wi-Fi connection yet. The next gate is a bounded no-credential method proof that calls `IWifi.start()` once and observes whether a WLAN/wiphy/rfkill surface appears.

V493 reuses the existing V466 raw hwbinder method runner, but adds a V492 registration-present precondition.

## Preconditions

V493 requires:

```text
V492: Samsung ISehWifi/default registration present
```

The runner enforces this through:

```text
--v492-manifest path/to/V492/manifest.json
```

The V492 manifest must show:

```text
decision=v492-samsung-registration-post-load-present
pass=true
live_result.matched_fqinstance=<non-empty>
wifi_bringup_executed=false
scan_connect_executed=false
external_ping_executed=false
```

Without that manifest, V493 remains blocked.

## Test Scope

V493 uses the already deployed helper v48 mode:

```text
--mode wifi-iwifi-start-surface
```

The live run may:

- start the private service-manager/hwservicemanager/HAL/CNSS surface
- query `IWifi/default` through raw hwbinder
- call `IWifi.start()` once only if the service handle is non-null
- observe `wlan*`, `phy*`, `/proc/net/wireless`, and Wi-Fi rfkill surfaces
- clean up all helper-owned children

It must not:

- scan/connect/link-up
- read or write Wi-Fi credentials
- start supplicant, wificond, or hostapd
- DHCP, route, or ping externally
- persist daemons or mutate boot/autostart state

## Approval

Required phrase:

```text
approve v493 post-registration IWifi.start surface proof only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Decision Rules

| decision | meaning |
|---|---|
| `v493-iwifi-start-post-registration-surface-observed-cleaned` | `IWifi.start()` created a WLAN surface and cleanup was clean; proceed to scan-only planning |
| `v493-iwifi-start-post-registration-no-surface-delta` | method returned but no WLAN surface appeared |
| `v493-iwifi-start-post-registration-transaction-failed` | method transaction ran but did not return cleanly |
| `v493-iwifi-start-post-registration-service-null` | `IWifi/default` handle was not returned despite V492 Samsung registration |
| `v493-iwifi-start-post-registration-blocked` | V492 evidence, helper, runtime, process, or Wi-Fi-clean precondition missing |

## Next Work

1. Run V490 policy-load proof.
2. Run V491 post-load domain proof.
3. Run V492 Samsung registration proof.
4. If V492 sees Samsung registration, run V493 preflight with the V492 manifest.
5. If V493 creates a WLAN surface cleanly, plan scan-only and then connect/DHCP/external-ping gates.
