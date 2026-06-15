# NATIVE_INIT V2427 — ACDB thread-set clone-child resume hardening

## Scope

- Unit: host-only helper hardening after V2426.
- Device action: none.
- Android handoff: none.
- Native replay: none.
- Calibration ioctl issued by helper: none.
- Persistent Magisk module: none.

## Problem closed

V2426 proved the V2425 staging fix but still captured `0` `/dev/msm_audio_cal` ioctls while logcat proved the Android-good ACDB edge on worker TID `4578`.

The private V2426 JSONL showed the observer did see that worker being cloned:

- `tracee-add tid=4578`
- `clone tid=834 child_tid=4578`
- `captured_entries=0`

Source inspection then found the implementation gap: the `PTRACE_EVENT_CLONE` branch recorded the child TID and resumed the parent task, but did not explicitly wait for, initialize, set options on, and syscall-resume the cloned child tracee.

That means V2426 is better explained as an M0 clone-child resume gap than as a Magisk delivery-timing miss.

## Change

`workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_threadset_v2423.c` now adds `initialize_cloned_child()`:

1. Adds the cloned child TID to the tracee table.
2. Waits briefly for the clone child stop with `waitpid-clone-child`.
3. Applies `PTRACE_O_TRACESYSGOOD | PTRACE_O_TRACECLONE` to the child.
4. Resumes the child with `PTRACE_SYSCALL`.
5. Emits `clone-child-resumed` for private JSONL diagnostics.

The parent tracee is still resumed after clone handling. Existing thread-set attach, fd-owner filtering, and private payload hashing behavior are unchanged.

## Magisk direction

M1 remains deferred.

The next evidence-quality step is not a temporary Magisk boot module; it is one fixed-M0 rerun with this clone-child resume patch. M1 becomes justified only if the fixed staged/running M0 observer still misses a logcat-proven `/dev/msm_audio_cal` edge.

If M1 becomes necessary later, it should follow the Wi-Fi-style pattern: temporary Android-side measurement packaging only, same observer semantics, earlier delivery timing, no native-init runtime dependency, no native speaker write, and no persistent module left behind.

## Private build check

A private AArch64 static stripped build was produced only for host validation:

- path: `workspace/private/builds/audio/v2427-acdb-threadset-clone-child-resume-helper/a90_acdb_ioctl_capture_threadset_v2423`
- SHA256: `763ecb9d9434dd30026b5c78d2cc25a5782c6f9d1b4ce9bacbc6197f36af3e7f`
- `file`: `ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped`

This binary is private and is not tracked.

## Next unit

Run a fresh exact-gated Android/Magisk M0 live capture with the fixed helper. Expected interpretation:

- `ioctl_entries > 0`: proceed to private payload decode and native replay boundary design.
- `ioctl_entries = 0` while logcat again proves ACDB on a traced/resumed child: then M1 temporary Magisk module design is justified as a timing/delivery escalation.
- staging/ADB failure: fix handoff, not M1.

Native ACDB replay remains blocked until raw ioctl order, decoded headers, private payload hashes, mem-handle policy, and cleanup behavior are pinned.

## Validation

- AArch64 static stripped build + `file`: pass.
- `python3 -m py_compile` on touched Python/tests: pass.
- Focused V2423 planner tests: 6 pass.
- Focused V2424 live-runner regression tests: 6 pass.
- Focused V2426 wrapper tests: 3 pass.
- Full unittest suite: 1155 pass.
- `git diff --check`: pass.
