# Native Init V2264 Boot-Window Runner Metadata Cleanup

Date: `2026-06-12`

## Summary

- Cycle: `V2264`
- Track: `T2 WLAN native-init surface/cleanup`
- Type: host-only live-runner metadata cleanup.
- Decision: `v2264-boot-window-runner-metadata-cleanup-pass`
- Result: `PASS`
- Device action: none.

## Track Selection

The north-star order was re-evaluated before selecting this unit.

T1 was not selected because the latest meaningful firmware_class/qcacld boundary
question remains closed by V2253, and no new independent kernel-observation
oracle was identified in the current state documents. Re-running generic
CPU-clock or the same firmware_class boundary observer would only re-confirm
known evidence.

Drop trigger:

```text
t1-fwclass-boundary-question-closed-no-new-independent-oracle
```

T2 was selected because V2263 left explicit live-runner phase/residual metadata
gaps. The smallest coherent remaining family was the V2222/V2223/V2225/V2227
boot-window preflight/plan/rollbackable handoff runner set.

## Changes

- Added shared `a90_transport` phase timing to:
  - `native_kernel_a90_boot_window_preflight_v2222.py`
  - `native_kernel_a90_boot_window_plan_v2223.py`
  - `native_kernel_a90_boot_window_handoff_v2225.py`
  - `native_kernel_a90_boot_window_handoff_v2227.py`
- Added residual-state metadata for the preflight-only, host-only planner, and
  flash-capable but dry-run-default handoff runners.
- Preserved existing runner behavior, confirmation gates, command arguments,
  and flash/rollback flow.
- Regenerated the revalidation script inventory.
- Updated `GOAL.md` and the current TODO map with the V2264 result.

## Inventory Delta

After regenerating `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md`:

- `native_kernel_a90_boot_window_preflight_v2222.py` now reports `Transport=shared,a90ctl-subprocess,bridge-wrapper`, `Live=yes`, `Phase=yes`, `Residual=yes`.
- `native_kernel_a90_boot_window_plan_v2223.py` now reports `Transport=shared`, `Live=yes`, `Phase=yes`, `Residual=yes`.
- `native_kernel_a90_boot_window_handoff_v2225.py` now reports `Transport=shared,a90ctl-subprocess`, `Live=yes`, `Phase=yes`, `Residual=yes`.
- `native_kernel_a90_boot_window_handoff_v2227.py` now reports `Transport=shared,a90ctl-subprocess`, `Live=yes`, `Phase=yes`, `Residual=yes`.
- Active live scripts without explicit phase timer markers: `4` (was `8`).
- Active live scripts without residual-state metadata: `4` (was `8`).
- Source-root delete-review entries remain `0`.

## Validation

```text
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 -m py_compile \
    workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_preflight_v2222.py \
    workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_plan_v2223.py \
    workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_handoff_v2225.py \
    workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_handoff_v2227.py \
    workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_preflight_v2222.py --help
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_plan_v2223.py --help
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_handoff_v2225.py --help
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_handoff_v2227.py --help
python3 workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py --write
git diff --check
```

## Safety Scope

- Host-only static validation.
- No script live execution beyond no-op `--help` parsing.
- No flash/reboot.
- No rollback action.
- No Wi-Fi scan/connect/DHCP/ping.
- No credential use.
- No route mutation.
- No live BPF/perf attach.
- No `probe_write_user` execution.
- No tracefs control write.
- No private log or raw device output added to public files.
