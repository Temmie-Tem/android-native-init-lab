# Kernel REPL bitmap/cpumask packed resident-session proof batch

Date: 2026-07-02 KST

## Scope

Promote a packed resident-session batch for bitmap, bit-scan, bitmap allocator,
and cpumask helper contracts. These are not `/proc` or `/sys` state getters; they
exercise owned-buffer input/output ABI forms that are useful for the REPL function
map.

The unit also hardens two host-side reliability issues found live:

- `_poke_bytes()` now uses an idempotent same-value poke retry for proof-owned
  scratch buffers only.
- `a90_repl_resident_session.py` health checks now retry validation failures such
  as a fragmented `selftest` body, not just transport exceptions.

No new boot image was built. Both live attempts used the existing v1-repl image and
rolled back to v2321.

## Candidate Set

Targets:

- `__bitmap_weight`
- `__bitmap_complement`
- `__bitmap_andnot`
- `__bitmap_or`
- `__bitmap_set`
- `__bitmap_clear`
- `__bitmap_subset`
- `bitmap_alloc`
- `bitmap_zalloc`
- `find_next_bit`
- `find_last_bit`
- `find_next_zero_bit`
- `cpumask_next`
- `cpumask_next_wrap`
- `cpumask_next_and`
- `cpumask_any_but`

Static gate:

- `call-safety-classify`: `ok=true`
- Tier counts: `SAFE-SCALAR=2`, `SAFE-WITH-VALID-PTR=14`
- The pointer targets use proof-owned bitmap/cpumask buffers.
- Generic arbitrary `poke` remains non-replayable; only `_poke_bytes()` owned
  scratch-buffer fills use same-value replay.

Dry-run gate:

- `target_count=16`
- `max_batch_size=30`
- Candidate image SHA256:
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback v2321 SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`

## Live Attempt 1: stopped, host reliability gap found

Private run directory:

`workspace/private/runs/kernel/repl-resident-session-bitmap-cpumask-packed-batch-20260701T185601Z/`

Result:

- `__bitmap_weight` flushed PASS.
- `__bitmap_complement` stopped during owned-buffer setup, before the target call.
- Error: `ReplTransientNoiseError` on `op=2` poke result capture, `replay_safe=False`.
- Rollback-finally returned to clean v2321.

Diagnosis: the failed operation was an owned-buffer fill with a deterministic word value.
Repeating that exact write is safe because the buffer is proof-owned and later verified by
peeks/canaries. The generic REPL poke must remain non-replayable, but `_poke_bytes()` can
be replay-safe for this narrow setup use case.

## Host Fixes

`a90_repl.py`:

- Added `ReplSession.poke_runtime_idempotent()`.
- Changed `_poke_bytes()` to use that method.
- Left `poke_runtime()` unchanged, so arbitrary poke still fails closed on a lost result.

`a90_repl_resident_session.py`:

- Health command execution and health validation are now separated.
- If `version`/`status`/`selftest` returns `rc=0 status=ok` but validation is incomplete
  or fragmented, the harness records the failed attempt, restarts the bridge, and retries
  within `--health-retries`.

## Live Attempt 2: target batch passed, rollback independently verified

Private run directory:

`workspace/private/runs/kernel/repl-resident-session-bitmap-cpumask-idempotent-poke-batch-20260701T190243Z/`

Batch result:

- Decision at batch level: `a90-repl-resident-session-batch-pass`
- Completed targets: `16/16`
- Per-target flush: all 16 target JSON files written
- Raw runtime values: private only

Target outcomes:

| Target | Outcome |
| --- | --- |
| `__bitmap_weight` | Owned bitmap popcount contract passed. |
| `__bitmap_complement` | Owned dst/src bitmap complement contract passed. |
| `__bitmap_andnot` | Owned dst/src/mask bitmap and-not contract passed. |
| `__bitmap_or` | Owned dst/two-source bitmap OR contract passed. |
| `__bitmap_set` | Owned bitmap bounded set range contract passed. |
| `__bitmap_clear` | Owned bitmap bounded clear range contract passed. |
| `__bitmap_subset` | Owned two-bitmap subset predicate contract passed. |
| `bitmap_alloc` | Owned bitmap allocation contract passed and cleanup completed. |
| `bitmap_zalloc` | Owned zeroed bitmap allocation contract passed and cleanup completed. |
| `find_next_bit` | Owned bitmap scan contract passed. |
| `find_last_bit` | Owned bitmap reverse scan contract passed. |
| `find_next_zero_bit` | Owned bitmap zero-scan contract passed. |
| `cpumask_next` | Owned cpumask next-CPU scan contract passed. |
| `cpumask_next_wrap` | Owned cpumask wrap scan contract passed. |
| `cpumask_next_and` | Owned dual-cpumask AND scan contract passed. |
| `cpumask_any_but` | Owned cpumask scan excluding one CPU contract passed. |

Rollback notes:

- Rollback flash completed.
- The pre-fix harness exited nonzero after rollback because the immediate `selftest`
  command returned `rc=0 status=ok` but its body was fragmented and did not include
  `fail=0`.
- The same `rollback-health.json` status command reported `selftest fail=0`.
- A manual bridge restart followed by `version`, `status`, and `selftest` independently
  confirmed clean `v2321-usb-clean-identity-rodata`, `BOOT OK`, and
  `selftest pass=11 warn=1 fail=0`.

Because `rollback_boot_ready` was not written before the pre-fix harness exit, this run is
not promoted as a canonical timing sample. The rollback gate is still satisfied by the
post-run independent health check.

## Timing

Attempt 2 timeline was canonical until rollback flash completion, then missed the final
`rollback_boot_ready` marker due to the pre-fix selftest body-fragmentation failure.

- Candidate flash: `63.147s`
- Candidate boot/health: `43.188s`
- Warm reboot: `33.230s`
- Batch REPL selftest: `32.222s`
- Live batch window: `465.868s`
- Rollback flash: `65.270s`
- Candidate-start to rollback-flash-done total: `704.820s`

The live batch is intentionally heavier than scalar getter batches because these proofs
perform many owned-buffer setup/readback operations.

Timing aggregate after this unit:

- Canonical timelines parsed: `36/86`
- This successful target batch was skipped by the aggregate because its timeline is missing
  `rollback_boot_ready`.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py workspace/public/src/scripts/revalidation/a90_repl_resident_session.py tests/test_a90_repl.py tests/test_a90_repl_resident_session.py`
- Focused retry-policy tests: generic poke remains non-replayable; `_poke_bytes()` retries
  same-value owned-buffer setup; resident health retries fragmented selftest bodies.
- Related unittest set covering the resident-session harness, command-buffer helpers,
  live-math fake transport, call-safety seed checks, and packed fake batches:
  `Ran 39 tests`, `OK`
- `call-safety-classify` for the 16 target names: `ok=true`,
  `SAFE-SCALAR=2`, `SAFE-WITH-VALID-PTR=14`
- Resident dry-run: `target_count=16`, `max_batch_size=30`, candidate and rollback SHA
  verified
- `analyze_repl_run_timing.py`

Live validation:

- Attempt 1 stopped before the second target call, rollback-finally clean.
- Attempt 2 proved all 16 target contracts and independently verified clean v2321 rollback.

## Decision

Promote the 16 bitmap/cpumask target-specific function-map proofs under their owned input
contracts. Promote the host reliability fixes for idempotent owned-buffer setup poke and
health validation retry.

Do not count attempt 2 as a canonical timing sample because the pre-fix harness did not
write `rollback_boot_ready`. Do not rerun the same batch just for timing; the target proofs
and rollback state are already verified, and further live work should move to the next
packed candidate family.
