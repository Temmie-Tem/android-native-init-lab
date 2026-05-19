# v314 Plan: Private Property Materialization Executor Scaffold

- date: `2026-05-19`
- scope: approval-aware executor scaffold for private property namespace materialization
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- status: planned

## Summary

v313 emitted the explicit approval packet for a future private property
materialization step. v314 converts that approval packet into a fail-closed
executor scaffold.

This is still not the live materialization step. The executor records the exact
planned device mutation sequence, validates prerequisites, validates approval
gates, and refuses to execute live materialization even when approval flags are
present. This keeps the next mutation boundary auditable before any private
runtime namespace work touches the device.

## Key Changes

- Add `scripts/revalidation/wifi_private_property_materialization_executor.py`.
- Consume:
  - `tmp/wifi/v312-private-property-runtime-layout/manifest.json`
  - `tmp/wifi/v313-private-property-materialization-approval/manifest.json`
- Support:
  - `plan`: produce planned steps and checks with no device mutation.
  - `run`: require exact approval phrase and flags, but fail closed because live
    materialization is intentionally not implemented in v314.
- Record that `device_commands_executed` is always `False` in v314.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_materialization_executor.py
python3 scripts/revalidation/wifi_private_property_materialization_executor.py \
  --out-dir tmp/wifi/v314-private-property-materialization-executor \
  plan
python3 scripts/revalidation/wifi_private_property_materialization_executor.py \
  --out-dir tmp/wifi/v314-private-property-materialization-executor-refuse \
  run || true
python3 scripts/revalidation/wifi_private_property_materialization_executor.py \
  --out-dir tmp/wifi/v314-private-property-materialization-executor-approved-refuse \
  --allow-device-mutation \
  --assume-yes \
  --approval-phrase "approve v314 private property namespace materialization only; no daemon start and no Wi-Fi bring-up" \
  run || true
git diff --check
```

Expected decisions:

- `private-property-materialization-executor-plan-ready`
- `private-property-materialization-executor-approval-required`
- `private-property-materialization-executor-live-not-implemented`

## Blocked Actions

- Global `/dev/__properties__` replacement.
- Global `/dev/socket/property_service` creation.
- Property mutation or `setprop`-like writes.
- service-manager or hwservicemanager start.
- Wi-Fi HAL, `wificond`, `supplicant`, `hostapd`, CNSS, or diag daemon start.
- Wi-Fi scan/connect/link-up/credential/DHCP/routing.

## Acceptance

- No device command and no ADB command.
- No generated file installation.
- No bind mount or namespace manipulation.
- Exact approval phrase is recognized but still cannot bypass the v314
  live-not-implemented gate.
- v315 must either implement live private materialization with a separate
  approval boundary or choose a safer intermediate proof.
