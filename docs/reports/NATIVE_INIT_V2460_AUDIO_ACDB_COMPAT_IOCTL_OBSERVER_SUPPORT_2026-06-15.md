# NATIVE_INIT_V2460_AUDIO_ACDB_COMPAT_IOCTL_OBSERVER_SUPPORT_2026-06-15

## Summary

V2460 is the host-only implementation unit requested by V2459. It updates the
Android-side diagnostic helper so it can observe both:

- native AArch64 ioctl syscall `29`; and
- compat AArch32/ARM ioctl syscall `54`.

No device action was performed. No native audio ioctl, mixer write, PCM write,
playback, flash, Magisk install, or Android handoff was run.

## Why This Was Needed

V2458 captured a valid Android-good speaker ACDB edge but did not capture
`/dev/msm_audio_cal` payload bytes. V2459 found that the target stock audio path
is 32-bit `audio.primary.msmnile.so` + `libacdbloader.so`, while the helper only
recognized AArch64 syscall `29`. The relevant 32-bit ioctl syscall is `54`, so
p12816 `ioctl_any_entry_count=0` was an observer ABI gap.

## Kernel Layout Basis

The stock arm64 ptrace code confirms the safe detection method:

- `kernel/ptrace.c` clamps the returned `PTRACE_GETREGSET NT_PRSTATUS`
  `iov_len` to `regset->n * regset->size`.
- for compat tasks, `arch/arm64/kernel/ptrace.c` exposes the AArch32 GPR
  regset as `COMPAT_ELF_NGREG=18` entries of `compat_elf_greg_t` (`uint32_t`);
- `compat_gpr_get()` copies AArch32 registers by index:
  - `r0` at index `0`;
  - `r1` at index `1`;
  - `r2` at index `2`;
  - `r7` at index `7`;
  - `pc` at index `15`;
  - `cpsr` at index `16`;
  - `orig_r0` at index `17`.

Therefore the helper can distinguish ABIs by returned regset length:

- `sizeof(struct user_pt_regs)` means AArch64; syscall number is `x8`;
- `18 * sizeof(uint32_t)` means AArch32; syscall number is `r7`;
- ioctl arguments are `x0/x1/x2` for AArch64 and `r0/r1/r2` for AArch32.

This keeps the implementation source-backed; it does not guess a compat layout
from the V2458 run.

## Implementation

Changed helper:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_diag_v2449.c`

Changes:

- renamed the comment scope to `V2449/V2460`;
- added `A90_COMPAT_ARM_NR_IOCTL=54`;
- added `A90_COMPAT_ARM_GPR_COUNT=18`;
- replaced the AArch64-only `get_regs()` path with `get_syscall_frame()`;
- detects ABI from `PTRACE_GETREGSET NT_PRSTATUS` returned `iov_len`;
- decodes AArch32 syscall number and args from `r7/r0/r1/r2`;
- keeps AArch64 syscall number and args from `x8/x0/x1/x2`;
- records `abi`, `syscall_nr`, and `regset_len` in `ioctl_entry`,
  `ioctl_exit`, and `ioctl_unmatched` JSON events;
- preserves existing TGID fd-owner matching through `--fd-pid`;
- preserves raw payload policy: bytes are copied only for fd-matched private
  payload events.

Updated planner/test metadata:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py`
- `tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py`

The planner now exposes source-state checks for:

- compat ARM ioctl filter;
- regset-length ABI detection;
- ABI metadata in JSON events.

## Safety Review

The helper still does not:

- open `/dev/msm_audio_cal`;
- issue `AUDIO_ALLOCATE_CALIBRATION`;
- issue `AUDIO_SET_CALIBRATION`;
- call `tinymix`;
- call `tinyplay`;
- perform native playback.

It remains an Android-good measurement helper only.

## Validation

Commands run:

```sh
aarch64-linux-gnu-gcc -O2 -static -s -Wall -Wextra \
  -o workspace/private/builds/audio/v2460-acdb-compat-observer/a90_acdb_ioctl_capture_diag_v2449 \
  workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_diag_v2449.c

file workspace/private/builds/audio/v2460-acdb-compat-observer/a90_acdb_ioctl_capture_diag_v2449

python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py \
  tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py

PYTHONPATH=workspace/public/src/scripts/revalidation:tests \
  python3 -m unittest tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py -v

PYTHONPATH=workspace/public/src/scripts/revalidation:tests \
  python3 -m unittest tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py --dry-run
```

Results:

- AArch64 static helper build passed.
- `file` reported a statically linked AArch64 executable.
- helper SHA256:
  `16274af43d6c9b054897d4d6d480935488bdddd88a5f92a110e66cace5e97ad6`.
- V2449 focused tests: `6/6` passed.
- V2451 hybrid focused tests: `8/8` passed.
- dry-run source-state reports:
  - `contains_compat_arm_ioctl_filter=true`;
  - `contains_regset_len_abi_detection=true`;
  - `contains_abi_metadata=true`;
  - `forbidden_ok=true`.

## Next Unit

Next meaningful unit is a bounded Android-good rerun with the V2460 helper:

- reuse the V2451/V2458 hybrid late-observer path;
- materialize the updated helper into the temporary M1 measurement capsule;
- run the same bounded Android framework `AudioTrack` speaker playback;
- verify that p12816 now reports `abi=aarch32`, `syscall_nr=54`, and either
  fd-matched `/dev/msm_audio_cal` payload events or a stronger negative with
  compat ioctl visibility;
- roll back to V2321 and require final `selftest fail=0`.

Native ACDB replay remains blocked until that rerun pins command order, decoded
headers, payload hashes, `mem_handle` lifetime, and cleanup policy.
