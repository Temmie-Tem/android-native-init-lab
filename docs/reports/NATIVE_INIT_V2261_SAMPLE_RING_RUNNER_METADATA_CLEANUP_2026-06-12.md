# Native Init V2261 Sample-Ring Runner Metadata Cleanup

Date: `2026-06-12`

## Summary

- Cycle: `V2261`
- Track: `T2 WLAN native-init surface/cleanup`
- Type: host-only live-runner metadata cleanup.
- Decision: `v2261-sample-ring-runner-metadata-cleanup-pass`
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

T2 was selected because V2260 left explicit live-runner phase/residual metadata
gaps. The smallest coherent remaining family was the V2212-V2216 raw/perf
sample-ring kernel-observation runner set.

## Changes

- Added shared `a90_transport` phase timing to:
  - `native_kernel_raw_frame_slots_v2212.py`
  - `native_kernel_raw_frame_sample_ring_v2213.py`
  - `native_kernel_perf_regs_frame_sample_ring_v2214.py`
  - `native_kernel_perf_regs_codeword_sample_ring_v2216.py`
- Added residual-state metadata for the no-flash, read-only BPF/perf live path.
- Added phase/residual contract lines to the generated V2212/V2213/V2214/V2216 public reports.
- Preserved existing runner behavior and command arguments.
- Regenerated the revalidation script inventory.
- Updated `GOAL.md` and the current TODO map with the V2261 result.

## Inventory Delta

After regenerating `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md`:

- `native_kernel_raw_frame_slots_v2212.py` now reports `Transport=shared,bridge-wrapper`, `Live=yes`, `Phase=yes`, `Residual=yes`.
- `native_kernel_raw_frame_sample_ring_v2213.py` now reports `Transport=shared,bridge-wrapper`, `Live=yes`, `Phase=yes`, `Residual=yes`.
- `native_kernel_perf_regs_frame_sample_ring_v2214.py` now reports `Transport=shared,bridge-wrapper`, `Live=yes`, `Phase=yes`, `Residual=yes`.
- `native_kernel_perf_regs_codeword_sample_ring_v2216.py` now reports `Transport=shared,bridge-wrapper`, `Live=yes`, `Phase=yes`, `Residual=yes`.
- Active live scripts without explicit phase timer markers: `13` (was `17`).
- Active live scripts without residual-state metadata: `13` (was `17`).
- Source-root delete-review entries remain `0`.

## Validation

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_kernel_raw_frame_slots_v2212.py \
  workspace/public/src/scripts/revalidation/native_kernel_raw_frame_sample_ring_v2213.py \
  workspace/public/src/scripts/revalidation/native_kernel_perf_regs_frame_sample_ring_v2214.py \
  workspace/public/src/scripts/revalidation/native_kernel_perf_regs_codeword_sample_ring_v2216.py \
  workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_raw_frame_slots_v2212.py --help
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_raw_frame_sample_ring_v2213.py --help
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_perf_regs_frame_sample_ring_v2214.py --help
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_perf_regs_codeword_sample_ring_v2216.py --help
python3 workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py --write
git diff --check
```

## Safety Scope

- Host-only static validation.
- No device I/O beyond no-op `--help` parsing.
- No flash/reboot.
- No Wi-Fi scan/connect/DHCP/ping.
- No credential use.
- No route mutation.
- No live BPF/perf attach.
- No `probe_write_user` execution.
- No tracefs control write.
- No private log or raw device output added to public files.
