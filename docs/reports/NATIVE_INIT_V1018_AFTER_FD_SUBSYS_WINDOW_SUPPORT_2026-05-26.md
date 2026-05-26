# V1018 After-Fd Subsystem Window Support

- date: `2026-05-26`
- scope: source/build-only helper support
- decision: `v1018-after-fd-subsys-window-support-pass`
- pass: `True`
- evidence: `tmp/wifi/v1018-after-fd-subsys-window-support/manifest.json`

## Summary

V1018 adds helper `v173` support for a scoped subsystem-window order:

```text
after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window
```

with trigger gate:

```text
post-upper-surface-no-wlfw
```

This removes the V1016 circular WLFW-precondition gate for the next live
experiment. The new path still does not scan, connect, use credentials,
configure DHCP/routes, or ping externally.

## Implemented

- Bumped `a90_android_execns_probe` to `v173`.
- Added the new service-manager order and gate to usage and validators.
- Required `post-upper-surface-no-wlfw` to pair with the new order.
- Shared the Wi-Fi HAL legacy/ext and `wificond` child set with the V1016 order.
- Preserved CNSS gating on Wi-Fi HAL + `wificond`.
- Added a post-upper-surface no-WLFW trigger readiness predicate.
- Added output markers for gate readiness and trigger execution.
- Added result label:
  `post-upper-surface-no-wlfw-trigger-clean`.
- Kept raw eSoC controller ioctls, notify, BOOT_DONE, scan/connect,
  credentials, DHCP/routes, and external ping disabled.

## Build Evidence

| Item | Value |
| --- | --- |
| artifact | `tmp/wifi/v1018-execns-helper-v173-build/a90_android_execns_probe` |
| sha256 | `63a2110d4b082ee6f1cd07d28c6d55e59335d0378089dac71824aff8f3903884` |
| linkage | statically linked, no dynamic section |

## Verifier Checks

All V1018 verifier checks passed:

- helper version marker `v173`
- new order and new gate usage strings
- order/gate validators
- gate-order validation
- shared Wi-Fi surface children
- new run order with post-upper-surface no-WLFW gate
- upper surface before CNSS
- CNSS gated on upper surface
- post-upper-surface trigger readiness contract
- trigger starts on the new gate
- summary/result markers
- cleanup coverage for expanded actors
- no scan/connect or raw eSoC controller expansion
- static artifact and strings confirmation

## Guardrails

V1018 did not deploy the helper, contact the device, start any live actor,
open `/dev/esoc-0` or `/dev/subsys_esoc0`, run eSoC ioctls, perform Wi-Fi
scan/connect, use credentials, configure DHCP/routes, ping externally, or write
boot images, partitions, firmware, GPIO, sysfs, or debugfs.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_after_fd_subsys_window_support_v1018.py
python3 scripts/revalidation/native_wifi_after_fd_subsys_window_support_v1018.py
```

Result:

```text
decision: v1018-after-fd-subsys-window-support-pass
pass: True
build_artifact_sha256: 63a2110d4b082ee6f1cd07d28c6d55e59335d0378089dac71824aff8f3903884
```

## Next

Proceed in separate units:

1. V1019 deploy-only helper `v173`.
2. V1020 bounded live scoped subsystem-window gate.
3. Only if WLFW/BDF/`wlan0` or equivalent lower readiness appears, plan
   scan/connect and external ping.
