# Kernel Security Tier-2 Runtime Kernel REPL - Scheduler Counter Batch Attempt 2 Aborted

Date: 2026-07-01

## Result

ABORTED BEFORE LIVE PROOF. No scheduler counter target was promoted.

This was the follow-up attempt after fixing the post-flash bridge cadence from
the prior scheduler-counter run. The corrected cadence worked: after candidate
flash the host restarted the bridge, waited `12s`, then used
`a90ctl --timeout 30 version -> selftest -> status`; all three candidate health
checks passed.

The run then stopped before the first REPL proof call because the ad-hoc Python
wrapper imported `a90_repl.py` directly via `importlib` without the script
directory on `sys.path`, so `_workspace_bootstrap` was not importable. No target
call was issued. The wrapper rolled back immediately, and final v2321 health
passed.

## Batch Targets

| target | intended contract | live result |
| --- | --- | --- |
| `nr_processes` | no arguments; read-only scheduler process count; sane positive scalar with bounded short-repeat drift | not called |
| `nr_running` | no arguments; read-only runnable task count; sane scalar with bounded short-repeat drift | not called |
| `nr_iowait` | no arguments; read-only iowait count; sane scalar with bounded short-repeat drift | not called |
| `nr_context_switches` | no arguments; read-only context switch counter; sane nondecreasing scalar | not called |

No function-map entry is promoted from this attempt.

## Static / Host Validation

Pre-attempt host validation passed:

- Corrected bridge cadence was tested on resident v2321:
  `a90_bridge.py restart`, `12s` settle, then
  `a90ctl --timeout 30 version/selftest/status`.
- `py_compile`: `a90_repl.py` and `tests/test_a90_repl.py`.
- Focused unittest targets:
  - `CallSafetyClassificationTests`.
  - `SelftestIntegrationTests.test_call_proof_scheduler_counter_batch_passes_with_no_arg_contracts`.
- CLI `call-safety-classify` over the scheduler neighbor set:
  - `SAFE-SCALAR`: `nr_processes`, `nr_running`, `nr_iowait`,
    `nr_context_switches`.
  - `DENY`: `nr_iowait_cpu`, `single_task_running`, `get_avenrun`,
    `si_swapinfo`.
- `git diff --check`: clean.

Post-attempt host-only fix added a proper batch entrypoint:

- New CLI: `a90_repl.py call-proof-batch target...`.
- It runs all selected targets in one `ReplSession` and writes combined private
  evidence through the existing `--evidence-dir` path.
- Validation passed:
  - `py_compile`.
  - `a90_repl.py call-proof-batch --help`.
  - `SelftestIntegrationTests.test_call_proof_batch_cli_runs_scheduler_targets_in_one_session`.
  - `git diff --check`.

This fixes the wrapper class that caused this attempt to abort: future attempts
can invoke the repo script normally instead of importing `a90_repl.py` from an
ad-hoc Python module.

## Live Attempt

Flash gates were followed:

- Rollback/fallback images were checked before flashing.
- Candidate `boot_linux_tier2_repl_v1_repl.img` SHA256:
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- Rollback `boot_linux_v2321_usb_clean_identity_rodata.img` SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img` SHA256:
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img` SHA256:
  `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.

Candidate flash:

- `native_init_flash.py` wrote boot only through `--from-native`.
- Recovery/TWRP ADB was reached before the boot write.
- Remote pushed image SHA matched the candidate SHA.
- Boot readback SHA matched the candidate SHA.
- The flash helper's built-in native-init `version/status` verification passed.
- Explicit candidate `version`, `selftest`, and `status` passed after bridge
  restart plus `12s` settle.

Abort point:

- The ad-hoc wrapper attempted to load `a90_repl.py` with `importlib`.
- That import path did not include the revalidation script directory.
- Python raised `ModuleNotFoundError: No module named '_workspace_bootstrap'`.
- No `run_call_proof` target was invoked and no REPL op ran after candidate
  health.

Rollback:

- Rollback to v2321 was performed through `native_init_flash.py`.
- Remote pushed image SHA matched the rollback SHA.
- Boot readback SHA matched the rollback SHA.
- The rollback helper's built-in native-init `version/status` verification
  passed.
- Explicit final `version`, `selftest`, and `status` passed after bridge restart
  plus `12s` settle.

Private logs and the reconstructed result JSON are kept out of git under
`workspace/private/runs/kernel/live-call-proof-scheduler-counter-batch-20260701-pass/`.

## Timing

Timeline object was written to private evidence as required by `GOAL.md`:

| marker | UTC timestamp |
| --- | --- |
| `candidate_flash_start` | `2026-06-30T21:03:14.130Z` |
| `candidate_flash_done` | `2026-06-30T21:04:17.924Z` |
| `candidate_boot_ready` | `2026-06-30T21:04:40.015Z` |
| `live_session_start` | not reached |
| `live_session_end` | not reached |
| `rollback_flash_start` | `2026-06-30T21:04:40.027Z` |
| `rollback_flash_done` | `2026-06-30T21:05:48.264Z` |
| `rollback_boot_ready` | `2026-06-30T21:06:09.076Z` |

Per-phase elapsed:

| phase | elapsed |
| --- | ---: |
| candidate flash helper total | `63.794s` |
| candidate flash start to boot ready | `85.885s` |
| live proof session | not reached |
| rollback flash helper total | `68.237s` |
| rollback flash start to boot ready | `89.049s` |
| candidate start to final rollback ready | `174.946s` |

## Next

Stop device attempts for this scheduler-counter sub-goal here. There are now
two aborted scheduler-counter attempts, and the active GOAL keeps the
`fails-twice -> stop` rule in force.

The host-only fix is in place for a future operator-approved run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/a90_repl.py call-proof-batch \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 30 \
  --dmesg-tail 24 \
  --evidence-dir workspace/private/runs/kernel/<next-run>/proof \
  nr_processes nr_running nr_iowait nr_context_switches
```

Any new flash should be treated as a fresh operator-approved attempt, not an
automatic retry loop.
