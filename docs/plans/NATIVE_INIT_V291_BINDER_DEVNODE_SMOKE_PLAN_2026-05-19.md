# Native Init v291 Binder Devnode Create/Cleanup Smoke Plan

- date: `2026-05-19`
- scope: temporary Binder devnode create/stat/cleanup smoke
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- target artifact: `scripts/revalidation/wifi_binder_devnode_smoke.py`
- prerequisite: v290 decision `binder-devnode-plan-ready`

## Summary

v290 produced exact Binder devnode candidates from read-only kernel metadata:

- `/dev/binder` -> `c 10 81`
- `/dev/hwbinder` -> `c 10 80`
- `/dev/vndbinder` -> `c 10 79`

v291 performs the smallest non-read-only validation step: create those three
nodes in native `/dev`, verify they are visible, then remove them. It does not
open the Binder devices, does not issue Binder ioctls, and does not start any
service manager or Wi-Fi daemon.

The state change is limited to tmpfs-like native `/dev` nodes and is cleaned up
within the same tool run. Reboot also clears this state.

## Reference Notes

- Android Binder domains map to `/dev/binder`, `/dev/hwbinder`, and
  `/dev/vndbinder`:
  https://source.android.com/docs/core/architecture/hidl/binder-ipc?hl=en
- The Linux misc-device framework records the assigned minor number for misc
  devices; v290 already verified sysfs and `/proc/misc` agree:
  https://docs.kernel.org/6.2/driver-api/misc_devices.html
- binderfs is not used here. It requires a binderfs mount and Binder control
  ioctl and was not available in v289/v290 evidence:
  https://docs.kernel.org/6.0/admin-guide/binderfs.html

## Procedure

1. Load v290 manifest and require decision `binder-devnode-plan-ready`.
2. Capture pre-state:
   - `version`
   - `stat /dev/binder`
   - `stat /dev/hwbinder`
   - `stat /dev/vndbinder`
3. Create nodes with native shell `mknodc`:
   - `mknodc /dev/binder 10 81`
   - `mknodc /dev/hwbinder 10 80`
   - `mknodc /dev/vndbinder 10 79`
4. Capture created-state with `stat`.
5. Cleanup with `run /cache/bin/toybox rm -f ...`.
6. Capture post-state with `stat` and require the nodes to be absent again.

## Guardrails

- No Binder device open.
- No Binder ioctl.
- No binderfs mount.
- No service-manager execution.
- No Wi-Fi daemon execution.
- No QMI/QRTR packet.
- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- No rfkill/ICNSS writes.
- No Android partition write.
- Cleanup runs even if creation/stat verification fails.

## Expected Decisions

PASS decisions:

- `binder-devnode-smoke-plan-ready`
- `binder-devnode-create-cleanup-pass`

Failure decisions:

- `binder-devnode-smoke-input-missing`
- `binder-devnode-create-failed`
- `binder-devnode-stat-failed`
- `binder-devnode-cleanup-failed`

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_binder_devnode_smoke.py \
  scripts/revalidation/wifi_binder_devnode_feasibility.py \
  scripts/revalidation/a90ctl.py
git diff --check
```

Live dry-run:

```bash
python3 scripts/revalidation/wifi_binder_devnode_smoke.py \
  --out-dir tmp/wifi/v291-binder-devnode-smoke-plan \
  plan
```

Live apply:

```bash
python3 scripts/revalidation/wifi_binder_devnode_smoke.py \
  --out-dir tmp/wifi/v291-binder-devnode-smoke-live-$(date +%Y%m%d-%H%M%S) \
  run --apply
```

## Acceptance

- All three `mknodc` commands return success.
- All three nodes are visible immediately after creation.
- All three nodes are absent after cleanup.
- The tool does not open Binder devices or start any Android service process.
- The next step is v292 Binder open-only helper smoke, not service-manager/HAL
  execution.
