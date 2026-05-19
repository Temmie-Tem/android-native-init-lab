# Native Init v289 Binder / Service-Manager Feasibility

- date: `2026-05-19`
- scope: read-only Binder and service-manager feasibility inventory
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- plan: `docs/plans/NATIVE_INIT_V289_BINDER_SERVICE_MANAGER_FEASIBILITY_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_binder_service_manager_feasibility.py`
- evidence:
  - plan mode: `tmp/wifi/v289-binder-service-manager-plan/`
  - live mode: `tmp/wifi/v289-binder-service-manager-live-20260519-135726/`

## Result

- decision: `binder-kernel-present-devnodes-missing`
- pass: `True`
- reason: Binder kernel support appears present, but native `/dev` Binder nodes are missing.

## Validation

Static validation passed:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_binder_service_manager_feasibility.py \
  scripts/revalidation/wifi_hal_framework_boundary_inventory.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Plan mode passed:

```bash
python3 scripts/revalidation/wifi_binder_service_manager_feasibility.py \
  --out-dir tmp/wifi/v289-binder-service-manager-plan \
  plan
```

Live read-only mode passed:

```bash
python3 scripts/revalidation/wifi_binder_service_manager_feasibility.py \
  --out-dir tmp/wifi/v289-binder-service-manager-live-20260519-135726 \
  run
```

## Findings

| Check | Status | Detail |
| --- | --- | --- |
| native version | present | `A90 Linux init 0.9.60 (v261)` |
| Binder IPC config | enabled | `CONFIG_ANDROID_BINDER_IPC=y` |
| Binder device config | configured | `CONFIG_ANDROID_BINDER_DEVICES=binder,hwbinder,vndbinder` |
| Binderfs config | missing | `CONFIG_ANDROID_BINDERFS=n` |
| `/proc/filesystems` binderfs | absent | binder filesystem not listed |
| `/proc/misc` Binder devices | present | `proc_misc_hits=3` |
| `/dev/binder` | absent | native devnode not visible |
| `/dev/hwbinder` | absent | native devnode not visible |
| `/dev/vndbinder` | absent | native devnode not visible |
| Binder sysfs surface | present | `binder_sysfs_hits=8` |
| service-manager binaries | present | `stat_hits=2`, `find_lines=4` |
| service-manager processes | absent | `process_count=0` |

## Interpretation

v288 showed that HAL and `wificond` execution is blocked by missing Binder
runtime surfaces. v289 narrows the first blocker: this is not a pure
kernel-support absence. The kernel exposes Android Binder support and registered
misc devices, but the native init environment does not create `/dev/binder`,
`/dev/hwbinder`, or `/dev/vndbinder`.

Binderfs is not currently visible through kernel config or `/proc/filesystems`,
so a binderfs-based plan is not the first candidate. The next candidate is a
separate, explicit private Binder devnode feasibility plan based on the
registered misc device metadata. That plan must still avoid starting service
managers or HALs until the devnode and manager model is proven.

## Guardrails Kept

- no `mknod`
- no binderfs mount
- no Binder ioctl
- no service-manager execution
- no Wi-Fi daemon execution
- no QMI/QRTR packet
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no rfkill/ICNSS writes
- no Android partition write
- `mountsystem ro` used only for read-only binary visibility

## Next

- v290 should plan a private Binder devnode feasibility step.
- The v290 plan must explicitly define whether any non-read-only primitive is
  allowed, because creating Binder device nodes is a behavior change.
- HAL, `wificond`, supplicant, hostapd, and Wi-Fi link-up remain blocked.
