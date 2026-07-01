# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: ktime_get_ts64

Date: 2026-07-01

## Scope

- Target proved: `ktime_get_ts64`.
- Result: live proof passed; target promoted under an owned `struct timespec64` result-slot contract.
- Device action: yes, boot partition only through
  `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`.
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`.
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Private evidence:
  `workspace/private/runs/kernel/live-call-proof-ktime-get-ts64-retry-20260701T000637Z/`.

This target extends the post-saturation REPL map from scalar/no-argument helpers into a state-writer
shape: a kernel timekeeping helper writing into an owned caller-provided result struct.

## Static Candidate

| Target | Link VA | Static shape | Source contract |
| --- | ---: | --- | --- |
| `ktime_get_ts64` | `0xffffff800815f534` | `SAFE-WITH-VALID-PTR`; x0 is an owned result slot | `extern void ktime_get_ts64(struct timespec64 *ts)` |

Static gates:

- Resolution method: `export-recovery`, verified, map agrees with export.
- Direct BL xrefs: `39`.
- Next-symbol boundary: `ktime_get_seconds` at `+0x138`.
- Source declaration: `include/linux/timekeeping.h:43`.
- First 24 instruction words matched the pinned identity bytes.
- C1 allowlist requires argument 0 to be an owned `struct timespec64` result slot.

Input contract:

- Allocate an owned kmalloc slot of `0x40` bytes.
- Initialize the 16-byte `struct timespec64` area with fill bytes before each call.
- Place a trailing canary after the struct.
- Call `ktime_get_ts64(ptr)`.
- Read back `tv_sec` and `tv_nsec`.
- Free the slot with `kfree`.

Return contract:

- Void call writes a sane monotonic time.
- `tv_sec` is nonnegative and below the 10-year proof sanity bound.
- `tv_nsec` is in `0..999999999`.
- Repeated readings are nondecreasing.
- Delta is bounded by the serial-REPL proof budget.
- Trailing canary is preserved and cleanup succeeds.

## Live Result

The final live proof passed:

| Case | `tv_sec` | `tv_nsec` | Delta | Result |
| --- | ---: | ---: | ---: | --- |
| `ktime_get_ts64-read-1` | `0x8e` | `0x28eb0361` | `n/a` | pass |
| `ktime_get_ts64-read-2` | `0x94` | `0x0a5c1823` | `0x14711d0c2` | pass |

All live checks passed:

- `nsec_in_range=true`
- `seconds_in_sane_range=true`
- `nondecreasing=true`
- `bounded_short_delta=true`
- `result_slot_changed=true`
- `canary_preserved=true`
- `cleanup_ok=true`

The first instrumented attempt failed only the original `5s` delta bound:

- Failure reason: `ktime_get_ts64 result slot failed contract in proof read 2: bounded_short_delta`.
- Observed delta: `0x14d8b7572` ns, about `5.596s`.
- The same failed attempt still had sane seconds, sane nanoseconds, nondecreasing readings, canary
  preservation, and cleanup success.

The code therefore changed the proof budget from `5s` to `30s`, matching the serial REPL transaction
cost while preserving the meaningful checks.

## Code Outcome

`ktime_get_ts64` is now represented in the call-proof machinery as:

- `SAFE-WITH-VALID-PTR`
- required pointer arg `0`: `owned-timespec64-result-slot`
- return kind: `void`
- live-proven function-map entry after the bounded result-slot proof

The proof code also now returns a structured fail summary for a `ktime_get_ts64` contract miss instead
of raising before evidence is written. That preserves `case_results` and `failure_reason` when a future
time-state proof fails a live contract.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-ktime-get-ts64-retry-20260701T000637Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash start to helper done | `65.0s` |
| candidate flash start to explicit health done | `102.0s` |
| first instrumented call-proof attempt | `16.0s` |
| relaxed call-proof attempt | `16.0s` |
| live session total | `92.0s` |
| rollback flash start to helper done | `65.0s` |
| rollback start to final explicit health done | `103.0s` |
| rollback start to final version retry done | `112.0s` |
| candidate start to final health done | `316.0s` |
| candidate start to final version retry done | `325.0s` |

## Validation

Device validation:

- Preflight confirmed candidate, v2321, v2237, and v48 image SHA values.
- Bridge status passed before flash.
- Baseline v2321 `version`, `selftest`, and `status` passed.
- Candidate flash used `native_init_flash.py`; candidate SHA/readback matched.
- Candidate helper health passed.
- Explicit candidate `version`, `status`, and retried `selftest` passed with `selftest fail=0`.
- Instrumented proof first captured the too-tight delta failure.
- Relaxed proof passed and wrote evidence JSON.
- Rollback to v2321 used `native_init_flash.py`; rollback SHA/readback matched.
- Final explicit `selftest` and `status` passed with `selftest pass=11 warn=1 fail=0`.
- Final `version` needed one standalone retry due serial framing noise; retry passed.

Host validation:

- `py_compile` for `workspace/public/src/scripts/revalidation/a90_repl.py` and
  `tests/test_a90_repl.py`.
- Focused tests for the `ktime_get_ts64` pass path and structured fail path: `Ran 2 tests`, `OK`.
- Classifier CLI for `ktime_get_ts64`: `SAFE-WITH-VALID-PTR=1`, `ok=true`.
- Full `tests.test_a90_repl`: `Ran 174 tests`, `OK`.
- `git diff --check`.

## End State

Final resident is v2321 (`v2321-usb-clean-identity-rodata`) with `selftest fail=0`.

`ktime_get_ts64` is promoted as a live-proven result-slot timekeeping state writer.
