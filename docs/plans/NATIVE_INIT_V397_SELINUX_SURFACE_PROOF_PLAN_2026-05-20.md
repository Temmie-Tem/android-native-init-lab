# Native Init v397 SELinux Surface Proof Plan

## Goal

Turn the V396 `servicemanager` fatal-log candidate into a concrete SELinux runtime-surface decision before attempting any service-manager repair, clean-start smoke, Wi-Fi HAL start, scan, or connect.

This is a read-only proof step. It may inspect native runtime files and mounted Android policy/context inputs, but it must not deploy helpers, start Android daemons, start Wi-Fi HAL, change SELinux enforcement, write policy, toggle rfkill, bind/unbind drivers, or bring up Wi-Fi.

## Starting Evidence

- approved V392 result: `docs/reports/NATIVE_INIT_V392_APPROVED_BACKCHAIN_CAPTURE_RESULT_2026-05-20.md`
- V396 symbolization: `docs/reports/NATIVE_INIT_V396_FRAME_ELF_SYMBOLIZATION_2026-05-20.md`
- V396 evidence: `tmp/wifi/v396-frame-elf-pull-20260520-073940/`

V396 removed the missing-ELF blocker and localized the `servicemanager` abort path:

- `liblog.so + 0x63bc` -> `__android_log_set_aborter`
- `libbase.so + 0x16188` -> `android::base::LogMessage::~LogMessage()`
- `servicemanager + 0x8294` -> fatal-log return site near `frameworks/native/cmds/servicemanager/Access.cpp`

Relevant pulled strings:

- `Check failed: selinux_status_open(true ) >= 0`
- `Check failed: gSehandle != nullptr`
- `Check failed: getcon(&mThisProcessContext) == 0`
- `frameworks/native/cmds/servicemanager/Access.cpp`

## External Source Notes

AOSP `servicemanager` `Access::Access()` sets SELinux callbacks and then performs fatal `CHECK` calls for `selinux_status_open(true /*fallback*/)` and `getcon(&mThisProcessContext)`. The same file also fatal-checks the service context handle in `getSehandle()`.

AOSP `libselinux` `selinux_status_open()` opens and maps the SELinux kernel status page at the discovered SELinux mount plus `/status`; when fallback is requested it can use netlink, but it still depends on SELinux mount discovery and related runtime state.

References:

- https://android.googlesource.com/platform/frameworks/native/+/4257ea6038/cmds/servicemanager/Access.cpp
- https://android.googlesource.com/platform/external/selinux/+/refs/heads/main/libselinux/src/sestatus.c
- https://android.googlesource.com/platform/external/selinux/+/refs/heads/main/libselinux/src/init.c

## Scope

Add `scripts/revalidation/wifi_service_manager_selinux_surface_proof.py` with:

- `plan`: host-only guardrail manifest.
- `run`: read-only native inventory.

The run mode should collect:

- `version`, `status`, and `mountsystem ro`.
- `/proc/filesystems` and `/proc/mounts` SELinux evidence.
- `/sys/fs/selinux`, `/sys/fs/selinux/status`, `/sys/fs/selinux/enforce`, `/sys/fs/selinux/null`, `/sys/fs/selinux/policy`, and service-manager class/perms visibility.
- mounted Android service context files:
  - `plat_service_contexts`
  - `system_ext_service_contexts`
  - `product_service_contexts`
  - `vendor_service_contexts`
  - `odm_service_contexts`
  - corresponding `*_hwservice_contexts`
  - both direct mount paths such as `/mnt/system/system_ext/...` and system-as-root nested paths such as `/mnt/system/system/system_ext/...`
- focused read-only grep for `servicemanager`, `hwservicemanager`, `wificond`, `wifi`, and `android.hardware.wifi` in context files.
- V392 private preexec context evidence for `/dev/binder`, `/dev/__properties__`, and `/sys/fs/selinux/null`.
- V396 fatal-string evidence and framechain decision.

## Decision Rules

V397 should return one of:

- `service-manager-selinux-surface-native-ready-private-proof-needed`
  - native SELinux status and service context inputs are visible, but V392 private preexec evidence does not prove `/sys/fs/selinux/status` visibility inside the helper namespace.
- `service-manager-selinux-status-native-missing`
  - native `/sys/fs/selinux/status` is absent or unreadable.
- `service-manager-selinux-context-inputs-missing`
  - service context files needed by `servicemanager` are missing from the mounted Android tree.
- `service-manager-selinux-surface-manual-review`
  - required evidence is mixed or too weak to classify.

The expected first useful result is likely `native-ready-private-proof-needed`, because V392 helper v21 only printed `/sys/fs/selinux/null` in the private context and did not prove `/sys/fs/selinux/status`.

## Validation Plan

Static validation:

```text
python3 -m py_compile scripts/revalidation/wifi_service_manager_selinux_surface_proof.py
```

Plan-only validation:

```text
python3 scripts/revalidation/wifi_service_manager_selinux_surface_proof.py \
  --out-dir tmp/wifi/v397-selinux-surface-plan \
  plan
```

Expected plan result:

```text
decision: service-manager-selinux-surface-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Read-only live validation:

```text
python3 scripts/revalidation/wifi_service_manager_selinux_surface_proof.py \
  --out-dir tmp/wifi/v397-selinux-surface-$(date +%Y%m%d-%H%M%S) \
  run
```

Expected live guardrails:

```text
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next Step

If V397 returns `native-ready-private-proof-needed`, proceed to V398 helper v22 private-context expansion: add read-only preexec context lines for `/sys/fs/selinux`, `/sys/fs/selinux/status`, `/sys/fs/selinux/enforce`, and service context files inside the private root before any `servicemanager` start.
