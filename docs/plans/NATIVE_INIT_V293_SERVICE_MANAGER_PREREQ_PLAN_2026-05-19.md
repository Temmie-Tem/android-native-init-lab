# Native Init v293 Service-Manager Prerequisite Model Plan

- date: `2026-05-19`
- scope: read-only Android service-manager prerequisite model
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_service_manager_prereq_model.py`
- prerequisite: v292 decision `binder-open-only-smoke-pass`

## Summary

v292 removed the lowest Binder device blocker: native init can temporarily
create Binder devnodes and open/close them. v293 does not start any Android
service-manager process. Instead, it maps the remaining prerequisites before a
future service-manager dry-run can be considered.

The expected outcome is still blocked. Service-manager binaries being visible
is not enough; Android service managers also depend on property runtime,
SELinux/domain assumptions, linker namespace/runtime files, and correct process
ordering.

## Reference Notes

- Android init defines services and service metadata, but native init is not
  running Android init's service supervisor:
  https://android.googlesource.com/platform/system/core/+/c5c532fc312c9e5a2f2b8fecbfc535af4ffcd245/init/README.md
- HIDL service discovery depends on `hwservicemanager` and Binder domains:
  https://source.android.com/docs/core/architecture/hidl/services
- Android Binder domains and service-manager split are distinct from merely
  opening Binder device nodes:
  https://source.android.com/docs/core/architecture/hidl/binder-ipc?hl=en

## Inputs

- v288 HAL/framework boundary inventory
- v292 Binder open-only smoke
- current live native read-only captures:
  - service-manager binary paths
  - service-manager process list
  - property runtime paths
  - SELinux mount visibility
  - linkerconfig/APEX/system/vendor runtime path visibility
  - mounted-system VINTF Wi-Fi visibility

## Checks

| Check | Meaning |
| --- | --- |
| v292 Binder open | Binder device open-only blocker is closed |
| service-manager binaries | Android binaries are visible but not automatically runnable |
| service-manager processes | whether any manager is already running |
| property runtime | `/dev/socket/property_service` or `/dev/__properties__` visibility |
| SELinux surface | SELinux state/policy surface that affects domains and permissions |
| linker runtime | `/system/bin/linker64`, `/linkerconfig`, `/apex`, system/vendor paths |
| VINTF Wi-Fi metadata | HAL declarations visible for later service publication reasoning |

## Guardrails

- No service-manager execution.
- No Binder ioctl.
- No Binder devnode creation in v293.
- No Wi-Fi daemon execution.
- No QMI/QRTR packet.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill/ICNSS writes.
- No Android partition write.
- `mountsystem ro` is allowed only for read-only visibility.

## Expected Decisions

PASS inventory decisions:

- `service-manager-prereq-model-ready`
- `service-manager-prereq-blockers-mapped`

Blocked/error decisions:

- `service-manager-prereq-input-missing`
- `service-manager-prereq-native-capture-failed`

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_service_manager_prereq_model.py \
  scripts/revalidation/wifi_binder_open_smoke.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Live read-only:

```bash
python3 scripts/revalidation/wifi_service_manager_prereq_model.py \
  --out-dir tmp/wifi/v293-service-manager-prereq-live-$(date +%Y%m%d-%H%M%S) \
  run
```

## Acceptance

- The tool confirms v292 Binder open-only PASS as an input.
- The tool maps remaining blockers without executing service managers.
- If property runtime or linker/runtime context is absent, service-manager
  execution remains blocked.
- The next step is a narrower property-runtime or service-manager dry-run plan,
  not Wi-Fi HAL/`wificond` execution.
