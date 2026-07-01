# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: nr_iowait

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-nr_iowait-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-nr-iowait-20260701T050434Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-nr-iowait-20260701T050434Z/timeline.json`

## Target

`nr_iowait(void)` was selected from the previously aborted scheduler-counter
batch as a fresh one-target proof. The earlier batch attempts recorded
`nr_iowait` as `not called`, and later one-target recovery runs promoted only
`nr_context_switches`, `nr_processes`, and `nr_running`. This run calls only
the IO-wait count getter through the checked `call-proof` CLI.

Trusted contract:

- No arguments.
- The function reads scheduler IO-wait counters and returns an `unsigned long`.
- A valid result is nonnegative, below the conservative sane count bound, and
  stable or bounded-drift across a short repeated call. `0` is a valid idle
  IO-wait count.
- No returned pointer is dereferenced or freed.

## Static Gate

- Address: `nr_iowait=0xffffff80080ee024`.
- Resolution: `disasm-signature+xref+map`, C1 verified.
- Source declaration: `extern unsigned long nr_iowait(void)` at
  `include/linux/sched/stat.h:21`.
- ABI: no pointer arguments.
- C1 safety tier: `SAFE-SCALAR`, no required pointer args.
- Direct BL xrefs: `2`.
- Next-symbol boundary: `nr_iowait_cpu` at `+0xa0`.
- Static word checks pinned all 40 words, including the `cpumask_next` loop
  over possible CPUs and the per-CPU IO-wait count load/add sequence.
- Same classifier run left already-promoted `nr_running` as a same-shape
  neighbor; `nr_iowait_cpu`, `single_task_running`, and `si_swapinfo` stayed
  `DENY`.

## Live Run

Flash gate:

- Fallback images `v2237` and `v48`, v2321 rollback image, and TWRP recovery
  were present before flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py --from-native`; pushed-image SHA
  and boot readback SHA both matched the candidate SHA.
- Candidate `version/status` passed in the flash helper.
- Explicit candidate `hide/selftest` passed on the first attempt with
  `pass=11 warn=1 fail=0`. A stray serial `A` appeared after the protocol END
  marker and did not affect the command result.

Observed public values:

| Case | Return | Delta from first | Result |
| --- | ---: | ---: | --- |
| read 1 | `0x0` | n/a | PASS |
| read 2 | `0x0` | `0x0` | PASS |

Both reads were inside the sane count range, `0` is valid for this IO-wait
counter, and the short repeat was stable. The target returned through the REPL
normally; no oops/panic signature was observed in the proof path. Post-proof
candidate health stayed clean:

- `status`: `selftest pass=11 warn=1 fail=0`, `pstore entries=0`.
- `selftest`: `pass=11 warn=1 fail=0`.

Rollback:

- Rollback to `boot_linux_v2321_usb_clean_identity_rodata.img` used
  `native_init_flash.py --from-native`.
- Pushed-image SHA and boot readback SHA matched the v2321 SHA.
- Helper `version/status` verification passed after reboot.
- Final explicit health first hit serial framing noise on `hide`; the same
  attempt's `version/selftest/status` still passed. A `12s`-settled retry then
  passed `hide/version/selftest/status` cleanly.
- Final resident `version/selftest/status` passed:
  `v2321-usb-clean-identity-rodata`, `selftest pass=11 warn=1 fail=0`.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-nr-iowait-20260701T050434Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `64.754s` |
| candidate flash start to boot ready | `65s` |
| candidate explicit health | `1s` |
| live call-proof | `6s` |
| post-proof candidate health | `1s` |
| rollback flash helper total | `66.103s` |
| rollback flash start to boot ready | `67s` |
| final health initial | `11s` |
| final health retry | `2s` |
| candidate start to final health done | `216s` |

Notes:

- The total includes serial resync/settle time after the final explicit `hide`
  framing failure and retry.
- No post-proof `busybox dmesg` log probe was run; health, pstore inventory,
  normal REPL return, and clean rollback are the side-effect/oops gates for
  this proof.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- Focused tests:
  - `SelftestIntegrationTests.test_call_proof_scheduler_counter_batch_passes_with_no_arg_contracts`
  - `CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers`
- Focused result: `Ran 2 tests in 18.391s`, `OK`.
- Static classifier:
  - `nr_iowait`: `SAFE-SCALAR`, `disasm-signature+xref+map`,
    `0xffffff80080ee024`.
  - `nr_running`: `SAFE-SCALAR`, already promoted in the previous unit.
  - `nr_iowait_cpu`, `single_task_running`, `si_swapinfo`: `DENY`.

## Function Map Entry

`nr_iowait` is live-proven under exactly this contract:

- No arguments.
- The return value is a sane nonnegative scheduler IO-wait count in this proof
  environment.
- Short repeated calls must be stable or bounded-drift.

This proof does not authorize neighboring scheduler helpers, arbitrary
scheduler-state mutation, mass calls, or relaxing the C1 fail-closed
identity/safety gate.
