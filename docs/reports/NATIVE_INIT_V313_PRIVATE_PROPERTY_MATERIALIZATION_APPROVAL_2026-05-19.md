# Native Init v313 Private Property Materialization Approval Report

- date: `2026-05-19`
- scope: host-only approval packet for future private property materialization
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V313_PRIVATE_PROPERTY_MATERIALIZATION_APPROVAL_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_materialization_approval.py`

## Summary

v313 generated the approval packet for the next live mutation boundary. It does
not perform materialization.

## Evidence

| item | path | result |
| --- | --- | --- |
| approval packet | `tmp/wifi/v313-private-property-materialization-approval/` | `private-property-materialization-approval-ready` |

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_materialization_approval.py
python3 scripts/revalidation/wifi_private_property_materialization_approval.py \
  --out-dir tmp/wifi/v313-private-property-materialization-approval \
  run
git diff --check
```

Result: PASS.

## Proposed Future Scope

- Copy v312 generated files to a private device working directory only.
- Materialize property files only inside a private mount/runtime namespace if
  supported.
- Verify read-only property lookup with a minimal test helper only.
- Remove private files or reboot native init for cleanup.

## Explicitly Not Approved

- Global `/dev/__properties__` replacement.
- Global `/dev/socket/property_service` creation.
- service-manager or hwservicemanager start.
- Wi-Fi HAL, `wificond`, `supplicant`, `hostapd`, CNSS, or diag daemon start.
- Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## Required Approval Phrase

```text
approve v314 private property namespace materialization only; no daemon start and no Wi-Fi bring-up
```

## Decision

- decision: `private-property-materialization-approval-ready`
- reason: approval packet is ready; live materialization still requires explicit
  operator approval.
- next step: v314 approved private namespace materialization executor.

