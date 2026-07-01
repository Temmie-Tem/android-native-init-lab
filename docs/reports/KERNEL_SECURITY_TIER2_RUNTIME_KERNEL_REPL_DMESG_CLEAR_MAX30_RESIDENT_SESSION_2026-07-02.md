# Kernel REPL result-channel hardening and max30 resident-session pass

Date: 2026-07-02 KST

## Scope

Harden the host-side REPL result channel after packed resident sessions exposed
legacy PID canary readback instability. The previous packed runs proved
`find_task_by_pid_ns` and `find_task_by_vpid` per-target, but did not promote the
full packed batch because older PID borrowed-pointer canaries failed after those
targets had flushed.

This unit changes only the host driver. It does not build or flash a new boot image.

## Host Change

`a90_repl.py` now uses `dmesg -c` for the normal REPL result path:

- Pre-write drain: `dmesg -c >/dev/null 2>/dev/null || dmesg >/dev/null 2>/dev/null`
- Post-write read: `(dmesg -c 2>/dev/null || dmesg) | tail -n N | grep -a 'A90R'`

This preserves the existing v1-repl printk format and avoids boot-image changes while
making each op consume only the newly produced kernel-log window. The older plain
`dmesg` fallback remains for compatibility.

An optional `A90M*` marker parser was added, but it is **not enabled by default**. A
live probe showed this kernel accepts `/dev/kmsg` user markers only in Linux kmsg record
format (`6,0,0,-;message`). A first marker-enabled live attempt reached candidate health
but failed the candidate REPL selftest before any batch target ran; it was rolled back
cleanly and is not promoted. The default path was then switched to `dmesg -c` without
markers.

## Live Attempt 1: marker-enabled probe, not promoted

Private run directory:

`workspace/private/runs/kernel/repl-resident-session-marker-window-max30-batch-20260701T182615Z/`

Result:

- Candidate flash completed and candidate health was clean.
- Candidate REPL selftest did not capture `A90R` for slide op after 3 attempts; stdout
  samples showed `A90M...E` marker records but no REPL result.
- No batch target ran.
- Rollback-finally completed to clean `v2321`.

Decision: do not enable marker mode by default and do not promote this run.

## Live Attempt 2: dmesg-clear max30 pass

Private run directory:

`workspace/private/runs/kernel/repl-resident-session-dmesg-clear-max30-batch-20260701T183207Z/`

Plan:

- `target_count=30`
- `max_batch_size=30`
- Batch:
  `find_task_by_pid_ns, find_task_by_vpid, pid_task, find_pid_ns, find_vpid, find_get_pid, get_task_pid, task_active_pid_ns, pid_nr_ns, pid_vnr, __task_pid_nr_ns, task_prio, task_curr, current_umask, in_group_p, in_egroup_p, get_taint, test_taint, sec_debug_is_enabled, sec_debug_level, sec_debug_get_reset_reason, sec_debug_get_reset_write_cnt, sec_debug_get_reset_reason_str, slab_is_available, debugfs_initialized, tracefs_initialized, cpu_mitigations_off, get_state_synchronize_rcu, get_state_synchronize_sched, is_boot_recovery`

Session summary:

- Decision: `a90-repl-resident-session-pass`
- Completed targets: `30/30`
- Completed batches: `1/1`
- Flash count: `2`
- Actual flash amortization: `0.0667 flash/target`
- Raw runtime values: private only
- Timeline errors: `[]`
- Warm reboot before batch: yes
- Rollback flashed once at session end: yes

The previous failure points were crossed:

- `find_vpid` passed with refcount path `6 -> 6 -> 5`.
- `find_pid_ns` passed with refcount path `6 -> 6 -> 5`.
- The full 30-target batch finished and wrote `batch-summary.json`.

## Timing

Canonical timeline events were present, including all required phase events.

- Candidate flash: `65.384s`
- Candidate boot/health: `53.497s`
- Warm reboot: `32.685s`
- Live batch window: `139.218s`
- Rollback flash: `64.286s`
- Rollback boot/health: `48.233s`
- Candidate-start to rollback-ready total: `437.139s`
- Measured wall time per target: `14.57s/target`

Run-timing aggregate after this pass:

- Canonical timelines parsed: `34/83`
- Resident-session projection with `batch_size=10`, `resident_batches=10`,
  `warm_reboot=15s`: `14.0s/target`, `21.2x` vs per-unit flash and `2.1x`
  vs per-unit in-boot batching

This is the first real max30 packed session matching the resident-session intent:
the measured `14.57s/target` is close to the model instead of the earlier one-target
resident cadence.

## Final Device State

Rollback health from the harness and an independent repo-local `a90ctl.py` recheck
confirmed clean `v2321`:

- Resident build: `v2321-usb-clean-identity-rodata`
- `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
- `status`: `BOOT OK`, `selftest fail=0`
- `selftest`: `pass=11 warn=1 fail=0`

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- Focused unittest set covering command-buffer helpers, marker-window parsing, live-math fake
  transport, call-safety classification, both task lookup proofs, and the packed fake PID
  borrowed batch: `Ran 26 tests`, `OK`
- `git diff --check`
- `a90_repl_resident_session.py --dry-run --max-batch-size 30 ...`: `ok=true`,
  `target_count=30`
- `/dev/kmsg` probe: plain `<6>message` was not visible, while
  `6,0,0,-;A90M...` was visible through `dmesg -c`
- `analyze_repl_run_timing.py`

Live validation:

- Marker-enabled attempt: failed before batch, rollback clean, not promoted
- `dmesg -c` default attempt: 30/30 target pass, rollback clean, final independent health clean

## Decision

Promote the host-side `dmesg -c` result-channel hardening and the max30 resident-session
run as packed-session proof. Keep kmsg marker mode opt-in only; it is useful for future
experiments but is not safe as the default REPL op path on this resident.

The next REPL function-map work can use packed resident sessions again. Keep the newer
rules: no one-target resident sessions, per-target flush, bounded batches, and fail-closed
call-safety gates.
