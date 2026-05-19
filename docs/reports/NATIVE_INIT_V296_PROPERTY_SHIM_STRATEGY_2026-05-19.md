# Native Init v296 Property Shim Strategy Model

- date: `2026-05-19`
- scope: host-side property shim strategy model
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V296_PROPERTY_SHIM_STRATEGY_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_property_shim_strategy.py`
- evidence: `tmp/wifi/v296-property-shim-strategy/`

## Result

- decision: `property-shim-strategy-capture-needed`
- pass: `True`
- reason: the static snapshot is useful, but it is missing selected runtime
  baseline keys.
- recommendation: `android-boot-property-capture`

## Validation

Static validation and model run passed:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_property_shim_strategy.py \
  scripts/revalidation/wifi_property_snapshot_model.py
git diff --check
python3 scripts/revalidation/wifi_property_shim_strategy.py \
  --out-dir tmp/wifi/v296-property-shim-strategy \
  run
```

## Model

| Item | Value |
| --- | --- |
| static property count | `248` |
| property context line count | `1264` |
| Wi-Fi property count | `7` |
| required present | `ro.build.version.sdk` |
| required missing | `ro.product.name`, `ro.hardware`, `ro.vendor.build.version.sdk` |

## Interpretation

Static property files are enough for a lookup-table design, but not enough to
confidently synthesize the Android runtime property view needed before a
service-manager dry-run. Missing runtime-like keys should be captured from a
normal Android boot before building any `/dev/__properties__` or property socket
shim.

## Guardrails Kept

- no property service creation
- no `/dev/socket` or `/dev/__properties__` writes
- no property value mutation
- no service-manager execution
- no Binder ioctl or Binder devnode creation
- no Wi-Fi daemon execution
- no QMI/QRTR packet
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no Android partition write

## Next

- v297 should be Android-boot property capture planning.
- That likely requires switching the phone to Android boot, collecting `getprop`
  and property-related metadata, then returning to native init.
- Do not create a property runtime or start service managers before v297 data is
  available.
