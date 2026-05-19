# Native Init v294 Android Property Runtime Feasibility Plan

- date: `2026-05-19`
- scope: read-only Android property runtime feasibility inventory
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_property_runtime_feasibility.py`
- prerequisite: v293 decision `service-manager-prereq-blockers-mapped`

## Summary

v293 showed that service-manager execution remains blocked mainly by missing
Android property runtime and absent service-manager process model. v294 isolates
the property blocker. It inventories the live native property surfaces and the
mounted Android property inputs, but does not create a property service, write
property areas, or start Android init/service-manager components.

Expected result: mounted Android property inputs are visible, but native
property runtime paths are absent. That means service-manager execution still
requires a separate property-runtime model or shim plan.

## Reference Notes

- Bionic property clients use `/dev/socket/property_service` for writes and the
  system property area for reads:
  https://android.googlesource.com/platform/bionic/+/c5fd81a/libc/bionic/system_properties.cpp
- Android init's property service loads property context files and serializes
  property info:
  https://android.googlesource.com/platform/system/core/+/refs/heads/android15-qpr2-s9-release/init/property_service.cpp
- Android SELinux compatibility documents split property context files such as
  platform and vendor property contexts:
  https://source.android.com/docs/security/features/selinux/compatibility

## Inputs

- v293 service-manager prerequisite model
- live native read-only captures:
  - `/dev/socket/property_service`
  - `/dev/__properties__`
  - property-related entries under `/dev`
  - mounted Android `*_property_contexts`
  - mounted Android `build.prop` and default property files

## Checks

| Check | Meaning |
| --- | --- |
| v293 prerequisite | service-manager blocker was property/runtime related |
| live property socket | whether property service socket exists |
| live property area | whether serialized property shared-memory area exists |
| mounted property contexts | whether Android context inputs are visible |
| mounted build props | whether static property input files are visible |
| SELinux property files | whether platform/vendor property labels can be inventoried |

## Guardrails

- No property service creation.
- No `/dev/socket` or `/dev/__properties__` writes.
- No property value mutation.
- No service-manager execution.
- No Binder ioctl or Binder devnode creation.
- No Wi-Fi daemon execution.
- No QMI/QRTR packet.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No Android partition write.
- `mountsystem ro` is allowed only for read-only visibility.

## Expected Decisions

PASS inventory decisions:

- `property-runtime-feasibility-ready`
- `property-runtime-inputs-visible-runtime-absent`
- `property-runtime-native-present`

Blocked/error decisions:

- `property-runtime-inputs-incomplete`
- `property-runtime-native-capture-failed`

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_property_runtime_feasibility.py \
  scripts/revalidation/wifi_service_manager_prereq_model.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Live read-only:

```bash
python3 scripts/revalidation/wifi_property_runtime_feasibility.py \
  --out-dir tmp/wifi/v294-property-runtime-live-$(date +%Y%m%d-%H%M%S) \
  run
```

## Acceptance

- The tool confirms whether property runtime is truly absent in native init.
- The tool distinguishes runtime absence from missing mounted Android property
  input files.
- No property service, Binder, service-manager, or Wi-Fi daemon action occurs.
- The next step is a property-runtime shim/model decision, not direct
  service-manager or HAL execution.
