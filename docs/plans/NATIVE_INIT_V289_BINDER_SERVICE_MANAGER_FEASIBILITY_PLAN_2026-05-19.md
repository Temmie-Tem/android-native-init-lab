# Native Init v289 Binder / Service-Manager Feasibility Plan

- date: `2026-05-19`
- scope: read-only Binder and service-manager feasibility inventory
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_binder_service_manager_feasibility.py`

## Summary

v288 proved that Wi-Fi HAL and `wificond` execution is blocked because native
init does not expose Binder device nodes, service-manager processes, or Android
property runtime. v289 narrows the first of those blockers: determine whether
Binder is absent from the kernel, present in the kernel but missing `/dev`
nodes, or available through binderfs-style runtime allocation.

v289 is read-only. It does not create device nodes, mount binderfs, start
`servicemanager`/`hwservicemanager`/`vndservicemanager`, start Wi-Fi daemons, or
send Binder/HIDL transactions.

## Reference Notes

- Android uses separate Binder domains: `/dev/binder`, `/dev/hwbinder`, and
  `/dev/vndbinder`; Android common kernels normally expose these through
  `CONFIG_ANDROID_BINDER_DEVICES="binder,hwbinder,vndbinder"`:
  https://source.android.com/docs/core/architecture/hidl/binder-ipc?hl=en
- Vendor and HAL processes need more than a device node: SELinux rules and
  service-manager add/find permissions are part of the runtime contract:
  https://source.android.com/docs/core/architecture/hidl/binder-ipc?hl=en
- binderfs can provide private Binder device instances, but allocation requires
  mounting binderfs and issuing `BINDER_CTL_ADD`; v289 only inventories support:
  https://docs.kernel.org/6.0/admin-guide/binderfs.html

## Inputs

- v288 report/evidence:
  - `tmp/wifi/v288-hal-framework-boundary-live-20260519-135154/manifest.json`
- current live native cmdv1 read-only captures:
  - `/proc/config.gz`
  - `/proc/filesystems`
  - `/proc/devices`
  - `/proc/misc`
  - `/proc/mounts`
  - `/sys/module/binder*`
  - `/sys/module/*binder*/parameters/devices`
  - `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder`
  - mounted-system service-manager binary paths

## Checks

| Check | Meaning |
| --- | --- |
| kernel config | whether `CONFIG_ANDROID_BINDER_IPC`, `CONFIG_ANDROID_BINDER_DEVICES`, and `CONFIG_ANDROID_BINDERFS` are visible |
| `/proc/misc` | whether misc Binder devices are registered despite missing `/dev` nodes |
| binder module sysfs | whether built-in/module parameters expose configured devices |
| binderfs support | whether `binder` filesystem support is visible |
| current `/dev` nodes | whether native init already created Binder nodes |
| service-manager binaries | whether Android binaries are visible through read-only system mount |
| service-manager processes | whether any manager is already running |

## Guardrails

- No `mknod`.
- No binderfs mount.
- No Binder ioctl.
- No service-manager execution.
- No Wi-Fi daemon execution.
- No QMI/QRTR packet.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill/ICNSS writes.
- No Android partition write.
- `mountsystem ro` is allowed only for read-only binary visibility.

## Expected Decisions

PASS inventory decisions:

- `binder-service-manager-feasibility-ready`
- `binder-kernel-present-devnodes-missing`
- `binderfs-feasible-devnodes-missing`

Blocked/error decisions:

- `binder-kernel-support-missing`
- `binder-service-manager-input-missing`
- `binder-service-manager-native-capture-failed`

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_binder_service_manager_feasibility.py \
  scripts/revalidation/wifi_hal_framework_boundary_inventory.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Live read-only:

```bash
python3 scripts/revalidation/wifi_binder_service_manager_feasibility.py \
  --out-dir tmp/wifi/v289-binder-service-manager-live-$(date +%Y%m%d-%H%M%S) \
  run
```

## Acceptance

- The tool distinguishes kernel support from missing `/dev` nodes.
- The tool confirms whether service-manager binaries exist but processes are
  absent.
- No device nodes are created and no service manager is started.
- The result gives a concrete v290 choice:
  - private Binder devnode/binderfs plan, or
  - service-manager model, or
  - retreat from HAL execution and focus on non-HAL CNSS diagnostics.
