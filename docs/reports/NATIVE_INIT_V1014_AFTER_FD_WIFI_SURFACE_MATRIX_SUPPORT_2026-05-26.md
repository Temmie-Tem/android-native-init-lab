# V1014 After-Fd Wi-Fi Surface Matrix Support

- date: `2026-05-26`
- scope: source/build-only helper support
- decision: `v1014-after-fd-wifi-surface-matrix-support-pass`
- pass: `True`
- evidence: `tmp/wifi/v1014-after-fd-wifi-surface-matrix-support/manifest.json`

## Summary

V1014 adds helper `v172` support for an after-fd Wi-Fi surface matrix order:

```text
after-mdm-helper-esoc-fd-with-wifi-surface
```

The order keeps the V1012 lower fd predicate first, then starts the Android
upper Wi-Fi surface actors before CNSS:

```text
property-shim
per_mgr_light
mdm_helper
esoc0-fd-gate
servicemanager
hwservicemanager
vndservicemanager
wifi_hal_legacy
wifi_hal_ext
wificond
cnss_diag
cnss_daemon
wlfw-precondition-gate
subsys_esoc0-open-child
```

The new path is still below scan/connect. It does not call `IWifi.start`, write
`qcwlanstate`, use credentials, configure DHCP/routes, or run an external ping.

## Implemented

- Bumped `a90_android_execns_probe` to `v172`.
- Added `--service-manager-order after-mdm-helper-esoc-fd-with-wifi-surface`.
- Expanded the CNSS/service-manager matrix child set from `8` to `11` for the
  new order.
- Reused existing identity contracts for Wi-Fi HAL legacy/ext and `wificond`.
- Added runtime markers for Wi-Fi HAL and `wificond` start attempts/results.
- Gated CNSS startup on Wi-Fi HAL and `wificond` startup for this new order.
- Kept eSoC controller ioctls, notify, BOOT_DONE, scan/connect, credentials,
  DHCP/routes, and external ping disabled.

## Build Evidence

| Item | Value |
| --- | --- |
| artifact | `tmp/wifi/v1014-execns-helper-v172-build/a90_android_execns_probe` |
| sha256 | `0c9b6d34be91211255a1359198329405806092fb9b4eeb4f24d3089e878df54d` |
| linkage | statically linked, no dynamic section |

## Verifier Checks

All V1014 verifier checks passed:

- version marker `a90_android_execns_probe v172`
- new order usage and validator
- expanded matrix child count
- upper actor path/contracts
- Wi-Fi surface order after fd/service-manager and before CNSS
- CNSS gate on upper-surface startup
- cleanup/postflight coverage for expanded children
- no scan/connect expansion
- no eSoC controller expansion
- static artifact and strings confirmation

## Guardrails

V1014 did not deploy the helper, contact the device, start any actor/daemon,
open `/dev/esoc-0` or `/dev/subsys_esoc0`, run eSoC ioctls, perform Wi-Fi
scan/connect, use credentials, configure DHCP/routes, ping externally, or write
boot images, partitions, firmware, GPIO, sysfs, or debugfs.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_after_fd_wifi_surface_matrix_support_v1014.py
python3 scripts/revalidation/native_wifi_after_fd_wifi_surface_matrix_support_v1014.py
```

Result:

```text
decision: v1014-after-fd-wifi-surface-matrix-support-pass
pass: True
build_artifact_sha256: 0c9b6d34be91211255a1359198329405806092fb9b4eeb4f24d3089e878df54d
```

## Next

Proceed in separate units:

1. V1015 deploy-only helper `v172`.
2. V1016 bounded live after-fd Wi-Fi surface matrix gate.
3. Only if WLFW/BDF/`wlan0` appears, plan scan/connect and external ping.
