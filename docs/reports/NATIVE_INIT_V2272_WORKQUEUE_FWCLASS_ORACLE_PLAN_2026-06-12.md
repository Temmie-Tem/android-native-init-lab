# V2272 Workqueue Firmware Class Oracle Plan

Date: `2026-06-12`

## Decision

`v2272-workqueue-fwclass-oracle-defined`

## Scope

Host-only T1 oracle definition. No boot image was built, no device was flashed,
no bridge/device command was run, and no Wi-Fi scan/connect/DHCP/ping action was
run.

## Why This Unit

V2271 made the loop-selection state explicit: no automatic safe unit was
available until a new T1 oracle, a concrete V2254 live criterion, or a revived
runner existed. The highest-priority path is T1, so this unit defines a new
kernel-observation oracle instead of falling into more WLAN or cleanup work.

This is not a repeat of the closed V2253 path:

- it does not use generic CPU-clock sampling;
- it does not use `/proc/*/stack` boundary snapshots;
- it observes static workqueue tracepoint function pointers copied from
  `work->func`.

## Source Basis

The V2272 plan generator checks these public/source facts:

| Check | Result |
| --- | --- |
| `workqueue_queue_work` tracepoint exists and records `function=work->func` | pass |
| `workqueue_execute_start` tracepoint exists and records `function=work->func` | pass |
| `firmware_class.c` defines `request_firmware_work_func()` | pass |
| `request_firmware_nowait()` initializes and schedules that work item | pass |
| dedicated firmware tracepoint source is absent | pass |
| V2216 exact codeword slide evidence exists | pass |
| V2253 closed the prior firmware_class boundary/sampler path | pass |

Primary source paths:

- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/include/trace/events/workqueue.h`;
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/base/firmware_class.c`;
- `docs/reports/NATIVE_INIT_V2216_PERF_REGS_CODEWORD_SAMPLE_RING_LIVE_2026-06-12.md`;
- `docs/reports/NATIVE_INIT_V2253_FWCLASS_BOUNDARY_STACK_LIVE_2026-06-12.md`.

## Artifact

`native_kernel_workqueue_fwclass_oracle_plan_v2272.py` writes:

- `docs/artifacts/native-init-frontier-candidates.json`.

Candidate:

```json
{
  "id": "t1-workqueue-fwclass-function-pointer-oracle",
  "track": "T1",
  "status": "ready_for_next_v_iteration",
  "safe_actionable_now": true
}
```

## Selector Result

After the candidate artifact is written, `native_init_frontier_select.py --json`
returns:

```json
{
  "decision": "frontier-selector-actionable-unit-present",
  "selected_track": "T1",
  "selected_reason": "new-independent-oracle-ready"
}
```

This reopens T1 for the next bounded unit.

## Next Runner Contract

The next V-iteration should implement/run a workqueue function-pointer observer:

1. capture `workqueue:workqueue_queue_work` and
   `workqueue:workqueue_execute_start` around the post-FWREADY
   `boot_wlan`/firmware_class window;
2. record `work`, `function`, `workqueue`, requested CPU, and executing CPU
   where available;
3. classify function pointers with same-boot exact-slide/codeword evidence;
4. treat hits on `request_firmware_work_func` or source-backed qcacld/CNSS
   workers as code-path identity evidence;
5. keep Wi-Fi scan/connect/DHCP/ping and credentials out of scope unless a later
   V-iteration explicitly requires them.

Expected discriminator:

- Positive: target window includes `request_firmware_work_func` or adjacent
  source-backed qcacld/CNSS worker function pointers.
- Negative: workqueue activity exists but no firmware_class/qcacld-HDD target
  function pointers appear, narrowing the target tail to a synchronous or
  non-workqueue path.
- Inconclusive: live tracepoint unavailable, same-boot function-pointer
  symbolization unavailable, or capture starts after the target window.

## Validation

Commands run:

```sh
PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_kernel_workqueue_fwclass_oracle_plan_v2272.py \
  workspace/public/src/scripts/revalidation/native_init_frontier_select.py \
  workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_kernel_workqueue_fwclass_oracle_plan_v2272.py --write --json

PYTHONPATH=workspace/public/src/harness:workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_init_frontier_select.py --json
```

Assertions passed:

- oracle plan decision is `v2272-workqueue-fwclass-oracle-defined`;
- every source/report check is `true`;
- candidate is `safe_actionable_now=true`;
- selector decision is `frontier-selector-actionable-unit-present`;
- selector chooses `selected_track=T1`;
- inventory classifies the plan generator as active host-only utility.

## Safety

This unit only reads source/docs and writes public metadata. It does not touch
private firmware contents, raw logs, credentials, boot images, device state,
tracefs, network state, or partitions.
