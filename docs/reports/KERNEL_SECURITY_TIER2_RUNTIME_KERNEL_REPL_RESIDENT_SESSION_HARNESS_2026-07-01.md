# Kernel Tier-2 REPL resident-session harness

Date: 2026-07-01

## Scope

Implemented the OPERATOR STEER resident-session harness change for the Tier-2
runtime kernel REPL. The goal is to stop doing one candidate flash plus one
rollback flash per bounded unit, and instead run:

`flash v1-repl once -> [warm reboot v1-repl -> bounded batch -> per-target flush] x N -> rollback v2321 once`.

No new boot image was built. All boot writes used the checked
`workspace/public/src/scripts/revalidation/native_init_flash.py` path.

## Public code changes

- `workspace/public/src/scripts/revalidation/a90_repl.py`
  - Added an optional `target_result_callback` to `run_call_proof_batch`.
  - Existing CLI behavior is unchanged; resident-session orchestration can now
    flush each completed target immediately.

- `workspace/public/src/scripts/revalidation/a90_repl_resident_session.py`
  - New resident-session orchestrator.
  - Verifies pinned v1-repl, v2321 rollback, deep fallback, and final fallback images.
  - Flashes v1-repl once, then runs bounded `--batch` groups.
  - Sends a mandatory warm reboot before each batch.
  - Runs health checks and REPL selftests after candidate boot and after each warm reboot.
  - Writes per-target private evidence with fsync immediately after each target callback.
  - Writes canonical `timeline.json` as a single top-level `events` array.
  - Rolls back to v2321 once at session end, with recovery-direct fallback if
    the native `recovery` command succeeds by disconnecting before the helper
    sees a clean return.
  - Rejects `[busy]`/`[err]` warm reboot responses instead of silently continuing
    into a no-reboot mega-session.
  - Adds bounded retry for safe health commands (`version/status/selftest`) after
    bridge restart. Generic call-proof targets are not auto-replayed.

- `tests/test_a90_repl.py`
  - Covers the per-target flush callback.

- `tests/test_a90_repl_resident_session.py`
  - Covers batch parsing, checked flash command construction, bridge restart CLI
    ordering, canonical timeline events, target-result flushing, and warm reboot
    busy rejection.

## Host validation

Passed:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  workspace/public/src/scripts/revalidation/a90_repl_resident_session.py \
  workspace/public/src/scripts/analysis/analyze_repl_run_timing.py \
  tests/test_a90_repl.py \
  tests/test_a90_repl_resident_session.py \
  tests/test_analyze_repl_run_timing.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl_resident_session \
  tests.test_analyze_repl_run_timing \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_batch_flush_callback_runs_after_each_target

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_repl

git diff --check
```

`tests.test_a90_repl` passed 206 tests.

Dry-run preflight passed for the default pinned inputs:

- v1-repl SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- v2321 rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- deep fallback SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- final fallback image present.

The timing aggregator was re-run after this change. With current private
canonical timelines:

```json
{
  "runs_used": 10,
  "timelines_found": 57,
  "old_flashes": 20,
  "resident_flashes": 2,
  "old_batch_sec": 287.328,
  "resident_per_target_sec": 15.311,
  "speedup_vs_unbatched_unit": 18.766,
  "speedup_vs_per_unit_in_boot_batch": 1.877
}
```

The increase from 52 to 57 timeline files is from the private smoke attempts
below; the aggregator still used the 10 canonical completed timelines.

## Live smoke status

Several private smoke attempts were run to exercise the new harness. Every
attempt ended with v2321 rollback and final native `selftest fail=0`.

Private evidence roots:

- `workspace/private/runs/kernel/repl-resident-session-smoke-20260701T111932Z/`
- `workspace/private/runs/kernel/repl-resident-session-smoke2-20260701T112731Z/`
- `workspace/private/runs/kernel/repl-resident-session-smoke3-20260701T113108Z/`
- `workspace/private/runs/kernel/repl-resident-session-smoke4-onebatch-20260701T113435Z/`
- `workspace/private/runs/kernel/repl-resident-session-smoke5-onebatch-20260701T113936Z/`

Findings from the smoke attempts:

- Harness bugs found and fixed:
  - Missing `peek_symbols` argument for `a90_repl.run_selftest`.
  - Rollback from native could fail after the device had already entered recovery; the harness now falls back to direct recovery flashing through the same checked helper.
  - `a90_bridge.py restart` option ordering was wrong; fixed and covered by test.
  - Warm reboot could be rejected by auto-menu `[busy]`; now pre-hides and fails closed on rejection.
  - Candidate health can hit `ATAT` serial noise; safe health commands now get a bounded bridge-restart retry.

- Best live reach:
  - v1-repl candidate flashed with matching readback SHA.
  - Candidate REPL selftest passed after bridge restart retry.
  - Mandatory warm reboot completed.
  - Post-warm-reboot health passed.
  - Batch live start was reached.
  - First call-proof target did not complete because `A90R` output was not captured
    for a non-replay-safe op; the batch stopped before any per-target promotion.

No resident-session target proof was promoted from these smoke attempts. The
remaining live blocker is transport/ring capture noise around the first
non-replay-safe call after warm reboot, not the flash-count/session design.

Final device state after the last attempt:

- Resident image: v2321 clean USB identity baseline.
- `version` returned `v2321-usb-clean-identity-rodata`.
- `selftest pass=11 warn=1 fail=0`.

## Next

Use the resident-session harness for the next live unit, but keep the first
batch small. If the first non-replay-safe call again loses `A90R`, stop and fix
the serial/ring capture path rather than replaying arbitrary call-proof targets.
