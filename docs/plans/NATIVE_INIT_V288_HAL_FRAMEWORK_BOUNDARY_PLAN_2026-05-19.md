# Native Init v288 HAL / Framework Boundary Inventory Plan

- date: `2026-05-19`
- scope: host-side and native read-only HAL/framework boundary inventory
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_hal_framework_boundary_inventory.py`

## Summary

v287 mapped the first missing native Wi-Fi service-order boundary to
`vendor.wifi_hal_ext`.  That means the next useful work is not another
`cnss-daemon` start-only retry.  Before any Wi-Fi HAL or `wificond` execution
attempt, native init must know which Android framework/HAL primitives are
visible, missing, or unsafe to emulate.

v288 inventories those boundaries only.  It does not start HAL daemons,
`wificond`, `cnss_diag`, supplicant, hostapd, or any QRTR/QMI path.

## Reference Notes

- Android init services define executable paths, arguments, classes, users,
  groups, capabilities, and optional interface declarations:
  https://android.googlesource.com/platform/system/core/+/c5c532fc312c9e5a2f2b8fecbfc535af4ffcd245/init/README.md
- Android VINTF device manifests and fragments declare HAL packages, versions,
  transports, interfaces, and instances loaded from vendor/ODM partitions:
  https://source.android.com/docs/core/architecture/vintf/objects
- HIDL HALs are IPC services and binderized HALs communicate through Binder-like
  transports:
  https://source.android.com/docs/core/architecture/hidl?hl=en
- Android HIDL service discovery depends on services registered with the service
  manager and the transport declared by the device manifest:
  https://source.android.com/docs/core/architecture/hidl/services
- Android 8+ binder domains distinguish `/dev/binder`, `/dev/hwbinder`, and
  `/dev/vndbinder`, with SELinux and service-manager permissions involved:
  https://source.android.com/docs/core/architecture/hidl/binder-ipc?hl=en

## Inputs

Default input manifests:

- `tmp/wifi/v206-android-icnss-cnss-map/manifest.json`
- `tmp/wifi/v210-vendor-asset-classifier/manifest.json`
- `tmp/wifi/v287-wifi-service-order-replay-model/manifest.json`

The tool should also collect current native read-only evidence in `run` mode:

- `version`, `status`
- `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder`
- `/dev/socket`, `/dev/socket/property_service`, `/dev/__properties__`
- `/sys/fs/selinux`
- native process list for `servicemanager`, `hwservicemanager`,
  `vndservicemanager`, Wi-Fi HAL, `wificond`, `cnss-daemon`, `cnss_diag`
- mounted system VINTF/interface visibility after safe `mountsystem ro`

## Boundary Checks

The inventory classifies:

| Boundary | Purpose | Expected v288 outcome |
| --- | --- | --- |
| Android service metadata | init rc user/group/capability/interface model | present from v206/v287 |
| Android VINTF Wi-Fi HAL declarations | HAL transport/interface/instance evidence | present from v206/v210 |
| Android HAL process domains | SELinux/user/process context reference | present from v206 |
| Binder device nodes | framework/app, HIDL, vendor IPC primitives | native visibility check |
| Service managers | `servicemanager`, `hwservicemanager`, `vndservicemanager` | native visibility check |
| Property runtime | `/dev/socket/property_service`, `/dev/__properties__` | native visibility check |
| Wi-Fi sockets/data paths | `/dev/socket/wifihal`, `wpa_wlan0`, data wifi sockets | native visibility check |
| SELinux surface | policy/domain assumptions for HAL services | native visibility check |
| Linker namespace | vendor/system/APEX/linkerconfig requirements | inventory-only; no execution |

## Guardrails

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
- `mountsystem ro` is allowed only as a read-only visibility step.

## Expected Decision

PASS inventory decisions:

- `hal-framework-boundary-inventory-ready`
- `hal-framework-boundary-native-blocked`

Blocked/error decisions:

- `hal-framework-boundary-input-missing`
- `hal-framework-boundary-native-capture-failed`
- `hal-framework-boundary-unsafe-policy`

`hal-framework-boundary-native-blocked` is still a successful inventory result:
it means the boundary map is complete enough to show HAL execution is not yet
safe.

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_hal_framework_boundary_inventory.py \
  scripts/revalidation/wifi_service_order_replay_model.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Plan mode:

```bash
python3 scripts/revalidation/wifi_hal_framework_boundary_inventory.py \
  --out-dir tmp/wifi/v288-hal-framework-boundary-plan \
  plan
```

Live read-only mode:

```bash
python3 scripts/revalidation/wifi_hal_framework_boundary_inventory.py \
  --out-dir tmp/wifi/v288-hal-framework-boundary-live-$(date +%Y%m%d-%H%M%S) \
  run
```

## Acceptance

- The tool reports HAL/framework blockers without running any Wi-Fi service.
- Android-side VINTF/HAL/service evidence is linked to native-side missing or
  visible runtime primitives.
- The result gives a concrete next step for v289.
- If binder/hwbinder/property/service-manager surfaces are absent, HAL and
  `wificond` execution remains blocked.

## Next

Likely v289 candidates:

1. if binder/HAL boundary is absent: read-only binder kernel/device-node
   feasibility and service-manager inventory;
2. if binder nodes exist but service managers are absent: service-manager
   feasibility model;
3. if HAL/framework remains too broad: return to `cnss-daemon` side with a
   diagnostic-specific `cnss_diag` observe-only plan.
