# V2268 Direct A90CTL Consolidation Groups

Date: 2026-06-12
Track: T2/T3 script consolidation after T1 downgrade
Type: host-only inventory tooling cleanup
Decision: `v2268-direct-a90ctl-consolidation-groups-pass`
Result: PASS

## Summary

V2268 makes the V2267 direct `a90ctl.py` reference signal actionable. The
inventory JSON now groups direct `a90ctl.py` references by expected impact and
recommended handling, and exposes the top group as `direct_a90ctl_top_group`.
This is still review-only: no runner behavior was changed and no live test was
run.

## Track Selection

- T1 was not selected because the latest kernel-observation boundary remains
  closed by V2253 and no new independent oracle was introduced for this unit.
- T2 Wi-Fi lifecycle is complete for the current V2254 baseline, and the active
  live phase/residual script backlog is closed.
- T2/T3 consolidation was selected because V2267 exposed direct `a90ctl.py`
  references but did not classify which ones matter first.

## Changes

- Added direct `a90ctl.py` candidate grouping to
  `inventory_revalidation_scripts.py`.
- Added `direct_a90ctl_candidate_groups` and `direct_a90ctl_top_group` to
  `consolidation_signals` in the inventory JSON.
- Refreshed inventory Markdown/JSON.
- Updated GOAL/TODO/risk text with the new top candidate group.

## Current Candidate Groups

```json
{
  "direct_a90ctl_reference_count": 15,
  "direct_a90ctl_top_group": {
    "group": "current_baseline_wifi_surface",
    "count": 1,
    "impact_score": 90,
    "names": ["native_wifi_detail_surface_handoff_v2255.py"]
  },
  "groups": [
    ["current_baseline_wifi_surface", 1, 90],
    ["flash_capable_kernel_handoff_runners", 6, 80],
    ["live_readonly_kernel_catalog_runners", 4, 60],
    ["legacy_bpf_anchor_runners", 4, 40]
  ]
}
```

Interpretation:

- If `native_wifi_detail_surface_handoff_v2255.py` is modified again, migrate
  its direct `a90ctl.py` command lists to shared transport helpers first.
- Flash-capable historical kernel handoff runners should only be migrated if
  they are revived or modified for a new bounded live run.
- Older BPF/perf anchor runners remain provenance/review-only unless reactivated.

## Validation

```bash
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation python3 -m py_compile \
  workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py --write >/tmp/v2268_inventory_write.log
python3 - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.json').read_text())
s = payload['consolidation_signals']
assert s['direct_a90ctl_reference_count'] == sum(g['count'] for g in s['direct_a90ctl_candidate_groups'])
assert s['direct_a90ctl_top_group']['group'] == 'current_baseline_wifi_surface'
print(json.dumps(s['direct_a90ctl_top_group'], indent=2, sort_keys=True))
PY
rg -n 'Direct `a90ctl.py` candidate groups|Direct `a90ctl.py` reference count|Machine-readable copy' \
  docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md
git diff --check
```

## Safety

This was host-only inventory tooling work. No live runner, flash, reboot, Wi-Fi
scan/connect/DHCP/ping, credentials, BPF/perf attach, tracefs write, raw log
capture, or device/partition write was performed.
