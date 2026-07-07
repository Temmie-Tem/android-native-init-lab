# S22+ Native-Init Observability Frontier Audit (2026-07-08)

## Verdict

Host-only frontier audit source is ready. It chooses the next observation path
from current evidence instead of repeating blind native-init candidates.

Current expected decision: EUD/OpenOCD is not ready because no host EUD endpoint
is present; no external UART adapter is currently visible; the M18 prefix
download P00/P10 artifacts validate. Therefore the next host-only unit is to
prepare the M18 P00 live gate source, not to run live immediately.

## Added

- `workspace/public/src/scripts/revalidation/s22plus_native_init_observability_frontier_audit.py`
- `tests/test_s22plus_native_init_observability_frontier_audit.py`

## What It Checks

- EUD/OpenOCD preflight by reusing the existing init-probe gate.
- Current host serial devices and whether they look like external USB-UART
  adapters rather than Samsung Android ACM.
- M18 prefix-download private artifacts:
  - top-level manifest exists and is host-only / live-flash-inert;
  - P00 and P10 manifests exist;
  - P00/P10 AP SHA256 values match the pinned build report;
  - APs are boot-only (`boot.img.lz4`);
  - safety flags reject configfs, ACM, block-device writes, persistent mounts,
    module binary injection, and non-Magisk baseline construction.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_native_init_observability_frontier_audit.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_native_init_observability_frontier_audit.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_native_init_observability_frontier_audit.py

S22+ native-init observability frontier: prepare-m18-prefix-p00-live-gate-source; eud_ready=0 uart_ready=0 m18_prefix_ready=1
```

## Next Gate

Do not flash from this audit. The selected next host-only unit is a guarded M18
P00 live-gate source/draft that pins the existing P00 AP SHA, requires fresh
AGENTS authorization, and rolls back to the pinned Magisk boot baseline after
the single supervised P00 run.
