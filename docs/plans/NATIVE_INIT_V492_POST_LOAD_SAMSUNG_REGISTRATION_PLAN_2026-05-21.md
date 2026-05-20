# Native Init V492 Post-Load Samsung Registration Plan

- Date: 2026-05-21 KST
- Scope: retry Samsung `ISehWifi/default` registration only after SELinux policy load and HAL-domain proof
- Status: implementation-ready; live V492 requires a successful V491 HAL-domain manifest
- Final Wi-Fi objective status: not achieved yet

## Background

Earlier bounded Samsung registration attempts proved that the private service-manager/hwservicemanager/HAL/CNSS surface can be started and cleaned, but `ISehWifi/default` did not register. V485 also showed the Samsung Wi-Fi HAL was still running as `kernel`, then aborting. The current hypothesis is that Android SELinux policy load plus a valid `u:r:hal_wifi_default:s0` handoff may unblock HAL registration.

V492 does not solve Wi-Fi by itself. It is the first post-policy/post-domain retry of the Samsung HAL registration surface.

## Preconditions

V492 requires:

```text
V490: policy load proof passed
V491: u:r:hal_wifi_default:s0 survives static post-exec proof
```

The runner enforces the V491 side through:

```text
--v491-manifest path/to/V491/manifest.json
```

The V491 manifest must show:

```text
decision=v491-post-load-domain-handoff-present
pass=true
policy_load_executed=false
init_reexec_executed=false
daemon_start_executed=false
wifi_hal_start_executed=false
wifi_bringup_executed=false
u:r:hal_wifi_default:s0 postexec_match=true
```

Without that manifest, V492 must remain blocked.

## Test Scope

V492 reuses the V483 private Samsung registration model with the currently deployed helper v48:

```text
--mode wifi-surface-composite-lshal-wait-samsung
```

The live run may start only:

- private `servicemanager`
- private `hwservicemanager`
- Samsung Wi-Fi HAL candidate
- bounded CNSS helper
- `lshal wait` for Samsung `ISehWifi/default` targets

It must not:

- load SELinux policy
- reexec PID1
- call Wi-Fi HAL methods
- start supplicant/wificond/hostapd
- scan/connect/link-up
- read credentials
- DHCP, route, or ping externally

## Approval

Required phrase:

```text
approve v492 post-load Samsung ISehWifi/default registration only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Decision Rules

| decision | meaning |
|---|---|
| `v492-samsung-registration-post-load-present` | Samsung `ISehWifi/default` appeared; proceed to bounded no-credential HAL readiness/method gate |
| `v492-samsung-registration-post-load-negative` | property shim and runtime ran, but Samsung target still did not register |
| `v492-samsung-registration-post-load-blocked` | V491 HAL-domain evidence, helper, runtime, process, or Wi-Fi-clean precondition is missing |

## Next Work

1. Run V490 policy-load proof.
2. Run V491 post-load domain proof with the V490 manifest.
3. If V491 proves `u:r:hal_wifi_default:s0`, run V492 preflight with the V491 manifest.
4. If V492 sees Samsung `ISehWifi/default`, move to no-credential HAL readiness methods.
5. Only after readiness works, proceed toward scan/connect/link-up, DHCP/routing, and external ping.
