# Native Init v288 HAL / Framework Boundary Inventory Report

- date: `2026-05-19`
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- boot image change: none
- result: PASS
- decision: `hal-framework-boundary-native-blocked`

## Summary

v288 adds a read-only HAL/framework boundary inventory tool.

The goal was to validate the v287 conclusion before any Wi-Fi HAL or `wificond`
execution attempt.  The result is clear: Android-side service/VINTF evidence is
present, but native init currently lacks the binder, service manager, and
property runtime surfaces needed for safe HAL/framework execution.

```text
decision: hal-framework-boundary-native-blocked
reason: native HAL/framework blockers:
  native-dev-binder
  native-dev-hwbinder
  native-dev-vndbinder
  native-service-manager-processes
  native-property-runtime
```

## Implemented

- Plan:
  - `docs/plans/NATIVE_INIT_V288_HAL_FRAMEWORK_BOUNDARY_PLAN_2026-05-19.md`
- Tool:
  - `scripts/revalidation/wifi_hal_framework_boundary_inventory.py`
- Evidence:
  - `tmp/wifi/v288-hal-framework-boundary-plan/`
  - `tmp/wifi/v288-hal-framework-boundary-live-20260519-135154/`

## Static Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_hal_framework_boundary_inventory.py \
  scripts/revalidation/wifi_service_order_replay_model.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Result: PASS.

## Plan Mode

```bash
python3 scripts/revalidation/wifi_hal_framework_boundary_inventory.py \
  --out-dir tmp/wifi/v288-hal-framework-boundary-plan \
  plan
```

Result:

```text
decision: hal-framework-boundary-inventory-ready
pass: True
```

## Live Read-Only Validation

Pre-check:

```bash
python3 scripts/revalidation/a90ctl.py --json version
```

Result:

```text
A90 Linux init 0.9.60 (v261)
```

Final v288 run:

```bash
python3 scripts/revalidation/wifi_hal_framework_boundary_inventory.py \
  --out-dir tmp/wifi/v288-hal-framework-boundary-live-20260519-135154 \
  run
```

Result:

```text
decision: hal-framework-boundary-native-blocked
pass: True
out_dir: /home/temmie/dev/A90_5G_rooting/tmp/wifi/v288-hal-framework-boundary-live-20260519-135154
```

## Boundary Result

| check | status | severity |
| --- | --- | --- |
| Android HAL service metadata | present | info |
| Android VINTF Wi-Fi HAL evidence | present | info |
| Android HAL process domains | present | info |
| Android Wi-Fi socket surface | present | info |
| Native `/dev/binder` | absent | blocker |
| Native `/dev/hwbinder` | absent | blocker |
| Native `/dev/vndbinder` | absent | blocker |
| Native service manager binaries | present | warning |
| Native service manager processes | absent | blocker |
| Native property runtime | absent | blocker |
| Native Wi-Fi socket surface | absent | info |
| Native SELinux surface | present | warning |
| Native mounted-system VINTF Wi-Fi evidence | partial-present | warning |
| Native `wificond` binary | present | warning |

## Interpretation

The Android reference side is coherent:

- Wi-Fi HAL services exist in init/VINTF evidence.
- Android processes run under expected HAL/Wi-Fi SELinux contexts.
- Android creates Wi-Fi socket surfaces such as `wifihal` and `wpa_wlan0`.

The native side is not HAL-ready:

- Binder device nodes are not visible in native `/dev`.
- `servicemanager`, `hwservicemanager`, and `vndservicemanager` are not running.
- Android property service socket and serialized property area are absent.
- `wificond` and service-manager binaries can be visible through read-only
  mounted system, but binary visibility is not execution readiness.

Therefore Wi-Fi HAL and `wificond` execution must remain blocked.

## Guardrails Verified

- No service execution.
- No `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, or hostapd
  start.
- No QMI payload.
- No QRTR packet.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill write.
- No ICNSS bind/unbind or `driver_override`.
- No firmware path mutation.
- No reboot/recovery/poweroff.
- No Android partition write.
- `mountsystem ro` was used only as a read-only visibility step.

## Next

Recommended v289:

```text
Binder / service-manager feasibility inventory
```

Reason:

- HAL and `wificond` are blocked mostly by missing Binder and service-manager
  runtime primitives, not by missing binaries.
- v289 should stay read-only unless a separate explicit plan approves creating
  binder device nodes or service manager processes.
- Property service emulation should remain a separate later decision because it
  can become mutable global Android runtime state.
