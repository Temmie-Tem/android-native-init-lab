# Kernel Security Tier-2 Runtime Kernel REPL - Scheduler Counter Batch Attempt Aborted

Date: 2026-07-01

## Result

ABORTED BEFORE LIVE PROOF. No scheduler counter target was promoted.

This unit prepared a same-session proof batch for the read-only scheduler
counter getters `nr_processes`, `nr_running`, `nr_iowait`, and
`nr_context_switches`. Host validation passed, but the live run stopped before
any target call because the wrapper's explicit post-flash `a90ctl version`
health check hit a serial END-marker timeout immediately after a bridge
restart.

The candidate and rollback flash helpers both completed successfully and each
helper's built-in native-init `version/status` verification passed. The device
was rolled back to the clean v2321 baseline, and a later explicit health check
with longer settle confirmed final resident v2321 with `selftest fail=0`.

## Batch Targets

| target | intended contract | live result |
| --- | --- | --- |
| `nr_processes` | no arguments; read-only scheduler process count; sane positive scalar with bounded short-repeat drift | not called |
| `nr_running` | no arguments; read-only runnable task count; sane scalar with bounded short-repeat drift | not called |
| `nr_iowait` | no arguments; read-only iowait count; sane scalar with bounded short-repeat drift | not called |
| `nr_context_switches` | no arguments; read-only context switch counter; sane nondecreasing scalar | not called |

Parked adjacent candidates remained denied:

- `nr_iowait_cpu` and `single_task_running`: generic C1 remains unverified for
  the leaf-map shape.
- `get_avenrun`: generic C1 remains unverified for the leaf-map shape and needs
  a separate exact-body C1 design before any live call.
- `si_swapinfo`: parked due spinlock/context-call surface.

## Static / Host Validation

Host validation passed before the device attempt:

- `py_compile`: `a90_repl.py` and `tests/test_a90_repl.py`.
- Focused unittest targets:
  - `CallSafetyClassificationTests`.
  - `SelftestIntegrationTests.test_call_proof_scheduler_counter_batch_passes_with_no_arg_contracts`.
- Full unittest suite: `tests.test_a90_repl` ran `165` tests, `OK`.
- `git diff --check`: clean.
- CLI `call-safety-classify` over the scheduler neighbor set:
  - `SAFE-SCALAR`: `nr_processes`, `nr_running`, `nr_iowait`,
    `nr_context_switches`.
  - `DENY`: `nr_iowait_cpu`, `single_task_running`, `get_avenrun`,
    `si_swapinfo`.

The fake integration test runs all four selected targets through one
`ReplSession`, asserts no-argument scalar calling, checks two-call return
contracts, and confirms raw runtime values stay out of the public summary.

## Live Attempt

Flash gates were followed:

- Rollback/fallback/TWRP artifacts were checked before flashing.
- Candidate `boot_linux_tier2_repl_v1_repl.img` SHA256:
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback `boot_linux_v2321_usb_clean_identity_rodata.img` SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img` SHA256:
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` SHA256:
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.

Baseline v2321 health passed before candidate flash:

- `version`: v2321 clean USB identity baseline.
- `selftest`: `pass=11 warn=1 fail=0`.
- `status`: `selftest pass=11 warn=1 fail=0`.

Candidate flash:

- `native_init_flash.py` wrote boot only through `--from-native`.
- Recovery/TWRP ADB was reached before the boot write.
- Remote pushed image SHA matched the candidate SHA.
- Boot readback SHA matched the candidate SHA.
- The flash helper's built-in native-init `version/status` verification passed.

Abort point:

- The wrapper restarted the host serial bridge, waited only a short settle, then
  ran explicit `a90ctl version` with the default 10 second timeout.
- That command failed with `A90P1 END marker not found before timeout` and a
  socket reconnect/reset symptom.
- No REPL `run_call_proof` target was executed.
- The wrapper immediately entered rollback.

Rollback:

- Rollback to v2321 was performed through `native_init_flash.py`.
- Remote pushed image SHA matched the rollback SHA.
- Boot readback SHA matched the rollback SHA.
- The rollback helper's built-in native-init `version/status` verification
  passed.
- The wrapper repeated the same too-short explicit post-rollback health check
  and hit the same END-marker timeout.
- A manual follow-up bridge restart, longer settle, and `a90ctl --timeout 30`
  health check passed: `version` reported v2321 and `selftest` reported
  `pass=11 warn=1 fail=0`.

Private logs and the reconstructed result JSON are kept out of git under
`workspace/private/runs/kernel/live-call-proof-scheduler-counter-batch-20260701/`.

## Timing

Timeline object was written to private evidence as required by `GOAL.md`:

| marker | UTC timestamp |
| --- | --- |
| `candidate_flash_start` | `2026-06-30T20:54:24.218Z` |
| `candidate_flash_done` | `2026-06-30T20:55:27.970Z` |
| `candidate_boot_ready` | `2026-06-30T20:55:27.970Z` |
| `live_session_start` | not reached |
| `live_session_end` | not reached |
| `rollback_flash_start` | `2026-06-30T20:55:43.026Z` |
| `rollback_flash_done` | `2026-06-30T20:56:58.207Z` |
| `rollback_boot_ready` | `2026-06-30T20:57:40.401Z` |

Per-phase elapsed:

| phase | elapsed |
| --- | ---: |
| candidate flash helper total | `63.706s` |
| candidate explicit bridge restart to health failure | `15.056s` |
| live proof session | `0.000s` |
| rollback flash helper total | `75.140s` |
| rollback explicit bridge restart to first health failure | `15.059s` |
| manual final bridge settle and health pass | `13.370s` |
| candidate start to final rollback-ready | `196.183s` |

## Next

Do not count this as a live proof. Before another device attempt, fix the
wrapper cadence host-side: after `native_init_flash.py` returns, restart the
bridge once, wait at least the empirically proven settle window, and use
`a90ctl --timeout 30 version -> selftest -> status` before entering the live
REPL proof. Because this attempt already rolled back after a health-check
failure, another flash should be treated as a new operator-approved device
attempt, not an automatic retry loop.
