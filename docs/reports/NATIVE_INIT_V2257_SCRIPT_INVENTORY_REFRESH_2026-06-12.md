# Native Init V2257 Script Inventory Refresh

Date: `2026-06-12`

## Summary

- Cycle: `V2257`
- Track: `T2 WLAN native-init surface/cleanup`
- Type: host-only script inventory classifier refresh and TODO map update.
- Decision: `v2257-script-inventory-refresh-pass`
- Result: `PASS`
- Device action: none.

## Track Selection

The north-star order was re-evaluated before selecting this unit.

T1 was not selected because V2253 closed the latest meaningful
firmware_class/qcacld boundary question: the target stack is visible before the
`WCNSS_qcom_cfg.ini` firmware_class feed, the after-feed worker has moved on,
and another generic CPU-clock or same-boundary observer would only re-confirm
established evidence without a new independent oracle.

Drop trigger recorded for this iteration:

```text
t1-fwclass-boundary-question-closed-no-new-independent-oracle
```

T2 was selected because V2256 promoted `v2254-wifi-detail-surface`, but the
active TODO map and script inventory still described the V2237/V2189-era cleanup
state.

## Changes

- Updated `inventory_revalidation_scripts.py` so current V22xx/V225x script
  families are classified intentionally instead of falling through to
  `delete-review`.
- Classified host-only `a90_kernel_vNNNN_*` analyzers as non-live to avoid
  false live-device metadata gaps from report text references.
- Classified reusable kernel symbolization/kallsyms utilities and local
  security regression utilities.
- Regenerated `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md` and
  `.json`.
- Updated `docs/plans/NATIVE_INIT_CURRENT_TODO_2026-06-08.md` for the V2254
  baseline and V2257 inventory state.

## Inventory Result

- Generated at: `2026-06-12T05:16:39.474648+00:00`
- Active entries: `107`
- Module entries: `6`
- Archive entries: `0`
- Delete-review entries: `0`
- Active live scripts without explicit phase timer markers: `23`
- Active live scripts without residual-state metadata: `23`
- Phase-timer-exempt live utilities: `2`
- Residual-state-exempt live utilities/helpers: `3`

This unit does not move or delete scripts. It makes the current cleanup backlog
explicit: the next script-consolidation unit should pick one active live runner
family and add/migrate shared phase/residual metadata rather than re-running the
whole inventory.

## Validation

```text
python3 workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py --write
python3 -m py_compile workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py
git diff --check
```

## Safety Scope

- Host-only.
- No device I/O.
- No flash/reboot.
- No BPF/perf attach.
- No tracefs control write.
- No Wi-Fi scan/connect/DHCP/ping.
- No route mutation.
- No credentials or private logs included in public output.
