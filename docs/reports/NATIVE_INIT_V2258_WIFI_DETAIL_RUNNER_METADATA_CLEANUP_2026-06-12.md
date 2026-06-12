# Native Init V2258 Wi-Fi Detail Runner Metadata Cleanup

Date: `2026-06-12`

## Summary

- Cycle: `V2258`
- Track: `T2 WLAN native-init surface/cleanup`
- Type: host-only live-runner metadata cleanup.
- Decision: `v2258-wifi-detail-runner-metadata-cleanup-pass`
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

T2 was selected because V2257 made the live-runner metadata cleanup backlog
explicit. The smallest current-baseline-related runner family was
`native_wifi_detail_surface_handoff_v2255.py`.

## Changes

- Added shared `a90_transport` phase timing to
  `native_wifi_detail_surface_handoff_v2255.py`.
- Added residual-state metadata for dry-run and live paths.
- Added phase/residual contract lines to the runner's generated public report.
- Regenerated the revalidation script inventory.
- Updated `GOAL.md` and the current TODO map with the V2258 result.

## Inventory Delta

After regenerating `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md`:

- `native_wifi_detail_surface_handoff_v2255.py` now reports:
  - `Transport`: `shared,a90ctl-subprocess`
  - `Live`: `yes`
  - `Phase`: `yes`
  - `Residual`: `yes`
- Active live scripts without explicit phase timer markers: `22` (was `23`).
- Active live scripts without residual-state metadata: `22` (was `23`).
- Source-root delete-review entries remain `0`.

## Validation

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_wifi_detail_surface_handoff_v2255.py \
  workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py
PYTHONPATH=workspace/public/src/harness \
  python3 workspace/public/src/scripts/revalidation/native_wifi_detail_surface_handoff_v2255.py --help
python3 workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py --write
git diff --check
```

## Safety Scope

- Host-only.
- No device I/O.
- No flash/reboot.
- No Wi-Fi scan/connect/DHCP/ping.
- No credential use.
- No route mutation.
- No BPF/perf attach.
- No tracefs control write.
- No private log or raw device output added to public files.
