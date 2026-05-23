# Native Init V664 Private Runtime Materialization Prep Report

- date: `2026-05-23 KST`
- status: `prep/preflight-blocked`; live Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_private_runtime_materialization_v664.py`
- plan evidence: `tmp/wifi/v664-private-runtime-materialization-plan-check/`
- preflight evidence: `tmp/wifi/v664-private-runtime-materialization-preflight-after-hide/`
- decision: `v664-private-runtime-materialization-blocked`

## Scope

V664 reuses V662 helper v108 and adds the V317 private property root to the
existing service `74`/`vndservicemanager_ready` registry snapshot flow. CNSS
retry remains disabled. Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and
external ping remain blocked.

## Implementation

- Adds `scripts/revalidation/native_wifi_private_runtime_materialization_v664.py`.
- Reuses V662 mode:
  `wifi-companion-service74-gated-vnd-service-manager-registry-snapshot-start-only`.
- Appends:
  `--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__`.
- Adds preflight checks for the V317 property root.
- Adds a materialization surface summary for:
  - `context.dev_properties.exists`;
  - property service shim state;
  - `/dev/socket/property_service`;
  - before/after registry `dirs_captured`.

## Validation

Executed:

```text
python3 -m py_compile scripts/revalidation/native_wifi_private_runtime_materialization_v664.py
python3 scripts/revalidation/native_wifi_private_runtime_materialization_v664.py --out-dir tmp/wifi/v664-private-runtime-materialization-plan-check plan
git diff --check
```

Plan validation passed with:

```text
decision: v664-private-runtime-materialization-plan-ready
pass: True
```

After hiding the native menu, preflight reduced the blockers to:

| blocker | status | next |
| --- | --- | --- |
| current-boot V490 policy-load proof | missing | rerun V490 after current boot |
| V641 clean-DSP state | stale/incomplete | rerun or re-arm V641 clean-DSP proof before V664 live |

All other V664 preflight checks passed, including helper v108, firmware path,
firmware partitions, `subsys_modem` cdev, real linkerconfig/APEX config, and the
V317 private property root.

## Next Gate

Refresh V490 and the V641 clean-DSP state, then rerun V664 preflight. A live run
should only proceed if both blockers are resolved in the same current boot.
