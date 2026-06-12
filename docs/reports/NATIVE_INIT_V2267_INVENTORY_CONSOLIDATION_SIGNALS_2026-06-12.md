# V2267 Inventory Consolidation Signals

Date: 2026-06-12
Track: T2/T3 script consolidation after T1 downgrade
Type: host-only inventory tooling cleanup
Decision: `v2267-inventory-consolidation-signals-pass`
Result: PASS

## Summary

V2267 turns the inventory report's consolidation section into a machine-readable
JSON contract. `inventory_revalidation_scripts.py` now emits a
`consolidation_signals` block alongside the human Markdown table, so future
cleanup can consume the same counts without re-parsing Markdown or re-deriving
lists by hand.

## Track Selection

- T1 was not selected because V2253 closed the firmware_class/qcacld boundary
  question and the later V2259-V2266 work found no new independent kernel oracle
  worth running in this unit.
- T2's active live phase/residual metadata backlog is already closed by V2266.
- T2/T3 consolidation was selected because the next safe unit is to preserve the
  inventory decision surface and prevent future manual drift.

## Changes

- Added `consolidation_signals` to
  `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.json`.
- Refactored Markdown rendering to use the same calculated signal block.
- Refreshed the inventory Markdown and JSON outputs.
- Updated GOAL/TODO state and the script-sprawl risk row to reflect that active
  live phase/residual gaps are now closed.

## Current Signal Values

```json
{
  "active_live_phase_residual_backlog_closed": true,
  "direct_a90ctl_reference_count": 15,
  "live_without_phase_timer_count": 0,
  "live_without_residual_state_count": 0,
  "source_delete_review_count": 0
}
```

Interpretation:

- Phase/residual migration backlog is closed for active live scripts.
- Source-root delete-review backlog remains zero.
- The next script-consolidation target, if one is needed, should come from the
  direct `a90ctl.py` reference list or duplicated older runner logic, not from
  phase/residual metadata cleanup.

## Validation

```bash
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation python3 -m py_compile \
  workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py --write >/tmp/v2267_inventory_write.log
python3 - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.json').read_text())
print(json.dumps(payload['consolidation_signals'], indent=2, sort_keys=True))
PY
rg -n 'Machine-readable copy|Direct .*reference count|Active live scripts without explicit phase timer markers|Active live scripts without residual-state metadata' \
  docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md
git diff --check
```

## Safety

This was host-only inventory tooling work. No live runner, flash, reboot, Wi-Fi
scan/connect/DHCP/ping, credentials, BPF/perf attach, tracefs write, raw log
capture, or device/partition write was performed.
