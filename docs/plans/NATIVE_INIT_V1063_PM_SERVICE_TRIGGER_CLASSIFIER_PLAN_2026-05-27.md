# Native Init V1063 PM Service Trigger Classifier Plan

Date: `2026-05-27`

## Goal

Classify the V1062 `pm-service` trigger/input gap without another live retry.

V1061 proved that global firmware visibility and helper modem pre-holder are no
longer the PM full-contract blocker.  It also proved that `pm_proxy_helper`
holds `/dev/subsys_modem`, while native `pm-service`/`per_mgr` remains
vndbinder-only and never opens `/dev/subsys_modem`.  V1063 narrows whether this
is still a property/provider-registration issue or a missing runtime input to
the running `pm-service` process.

## Method

1. Read V1024 Android-positive PM/eSoC fd evidence.
2. Read V1046 Android vendor init RC contract.
3. Read V1061/V1062 native PM full-contract evidence.
4. Reconcile older closure evidence:
   - V860 property-denial clean replay still had no subsystem fd;
   - V694 confirmed PeripheralManager vndservice registration;
   - V861 showed direct exec mapping alone was insufficient.
5. Inspect helper source for the current V1061 launch model: direct `execv`,
   default argv, PM actor order, and service-manager placement.
6. Emit a host-only route decision.

## Hard Gates

- Host-only; no device commands.
- No live retry, actor start, service-manager start, Wi-Fi HAL start,
  scan/connect, credentials, DHCP/routes, external ping, eSoC open/ioctl,
  sysfs/debugfs write, boot image write, partition write, firmware mutation, or
  Android handoff.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_service_trigger_classifier_v1063.py
python3 scripts/revalidation/native_wifi_pm_service_trigger_classifier_v1063.py run
```
