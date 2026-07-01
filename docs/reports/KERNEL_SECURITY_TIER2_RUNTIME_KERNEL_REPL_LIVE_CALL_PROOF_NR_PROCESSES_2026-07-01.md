# Kernel Security Tier-2 Runtime Kernel REPL - Live Call Proof: nr_processes

- Date: 2026-07-01
- Decision: `a90-repl-live-call-proof-nr_processes-pass`
- Scope: one-target live-call proof; boot partition only; rollback to `v2321`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/live-call-proof-nr-processes-20260701T044817Z/proof/a90_repl_evidence.json`
- Private timeline: `workspace/private/runs/kernel/live-call-proof-nr-processes-20260701T044817Z/timeline.json`

## Target

`nr_processes(void)` was selected from the previously aborted scheduler-counter
batch as a fresh one-target proof. The earlier batch attempts stopped before
any scheduler target call. This run calls only the process-count getter through
the checked `call-proof` CLI.

Trusted contract:

- No arguments.
- The function reads scheduler process counters and returns an `int`.
- A valid result is positive in this native-init proof, below the conservative
  sane count bound, and stable or bounded-drift across a short repeated call.
- No returned pointer is dereferenced or freed.

## Static Gate

- Address: `nr_processes=0xffffff80080ae02c`.
- Resolution: `disasm-signature+xref+map`, C1 verified.
- Source declaration: `extern int nr_processes(void)` at
  `include/linux/sched/stat.h:18`.
- ABI: no pointer arguments.
- C1 safety tier: `SAFE-SCALAR`, no required pointer args.
- Direct BL xrefs: `1`.
- Next-symbol boundary: `arch_release_task_struct` at `+0xa0`.
- Static word checks pinned all 40 words, including the `cpumask_next` loop
  over possible CPUs and the per-CPU process-count load/add sequence.
- Parked neighbors stayed denied in the static classifier:
  `nr_iowait_cpu`, `single_task_running`, and `si_swapinfo`.

## Live Run

Flash gate:

- Fallback images `v2237` and `v48`, v2321 rollback image, and TWRP recovery
  were present before flash.
- Baseline v2321 `version/status/selftest` passed before candidate flash.
- Candidate flash used `native_init_flash.py --from-native`; pushed-image SHA
  and boot readback SHA both matched the candidate SHA.
- Candidate `version/status` passed in the flash helper.
- The first explicit post-flash `hide/selftest` attempt hit `ATAT` serial
  framing noise. After a `12s` settle, bridge status was connected and explicit
  candidate `selftest` passed with `pass=11 warn=1 fail=0`.

Observed public values:

| Case | Return | Delta from first | Result |
| --- | ---: | ---: | --- |
| read 1 | `0x1c1` | n/a | PASS |
| read 2 | `0x1c1` | `0x0` | PASS |

Both reads were positive, inside the sane counter range, and stable across the
short repeat. The target returned through the REPL normally; no oops/panic
signature was observed in the proof path. Post-proof candidate health stayed
clean:

- `status`: `selftest pass=11 warn=1 fail=0`, `pstore entries=0`.
- `selftest`: `pass=11 warn=1 fail=0`.

Rollback:

- Rollback to `boot_linux_v2321_usb_clean_identity_rodata.img` used
  `native_init_flash.py --from-native`.
- Pushed-image SHA and boot readback SHA matched the v2321 SHA.
- Helper `version/status` verification passed after reboot.
- Final explicit health first hit serial framing noise, then `hide` plus a
  `12s`-settled retry passed.
- Final resident `version/selftest/status` passed:
  `v2321-usb-clean-identity-rodata`, `selftest pass=11 warn=1 fail=0`.

## Timing

Timeline source:

- `workspace/private/runs/kernel/live-call-proof-nr-processes-20260701T044817Z/timeline.json`.

| Phase | Elapsed |
| --- | ---: |
| candidate flash helper total | `72s` |
| candidate flash start to boot ready | `72s` |
| live call-proof | `6s` |
| post-proof candidate health | `2s` |
| rollback flash helper total | `73s` |
| rollback flash start to boot ready | `73s` |
| final health total | `66s` |
| final health retry | `1` retry |
| candidate start to final health done | `300s` |

Notes:

- The total includes serial resync/settle time after the explicit post-flash
  framing failure and final-health retry.
- No post-proof `busybox dmesg` log probe was run; health, pstore inventory,
  normal REPL return, and clean rollback are the side-effect/oops gates for
  this proof.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- Focused tests:
  - `SelftestIntegrationTests.test_call_proof_scheduler_counter_batch_passes_with_no_arg_contracts`
  - `CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers`
- Focused result: `Ran 2 tests in 18.488s`, `OK`.
- Static classifier:
  - `nr_processes`: `SAFE-SCALAR`, `disasm-signature+xref+map`,
    `0xffffff80080ae02c`.
  - `nr_iowait_cpu`, `single_task_running`, `si_swapinfo`: `DENY`.

## Function Map Entry

`nr_processes` is live-proven under exactly this contract:

- No arguments.
- The return value is a sane positive scheduler process count in this proof
  environment.
- Short repeated calls must be stable or bounded-drift.

This proof does not authorize neighboring scheduler helpers, arbitrary
scheduler-state mutation, mass calls, or relaxing the C1 fail-closed
identity/safety gate.
