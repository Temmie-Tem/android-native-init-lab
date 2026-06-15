# NATIVE_INIT_V2526_AUDIO_ACDB_OWNPROCESS_EXIT_GROUP_HOST_ONLY_2026-06-16

## Scope

- Unit: V2526 host-only helper fix for the V2512 exec-linked own-process ACDB helper.
- Trigger: V2524 showed the helper wrote an `acdb_loader_init_v3` error event (`code=-12`) but the host command still timed out after `60s`.
- Goal: ensure helper error exits terminate the whole helper process even if ACDB libraries created additional threads.

## Root Cause Hypothesis

The V2512 helper used the ARM32 `exit` syscall only:

- `exit` terminates the calling thread.
- If `acdb_loader_init_v3()` spawned ACDB/ACPH/RTAC-related worker threads before returning `-12`, a raw `exit` can leave the process group alive and keep `adb shell su -c ...` waiting until the host-side timeout.
- This matches V2524: the helper emitted an error event immediately, but the command did not return before the runner timeout.

## Change

- Added ARM32 `exit_group` syscall support:
  - `A90_NR_EXIT_GROUP 248`
  - `a90_exit()` now calls `exit_group(code)` first, then falls back to `exit(code)`.
- Added a build-script source-state invariant:
  - `uses_exit_group`
- Added focused test coverage that asserts the invariant is present.

## Boundary

- Host-only source/build/test unit.
- No device action, no flash, no Android handoff, no HAL injection, no playback, no native speaker write, and no native `/dev/msm_audio_cal` SET ioctl.
- Raw payloads and rebuilt helper binaries remain under `workspace/private/` only.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2512.py tests/test_build_android_acdb_ownprocess_get_exec_linked_v2512.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests/test_build_android_acdb_ownprocess_get_exec_linked_v2512.py`
  - Result: `5` tests passed.
- Cross-build using the private Android ARM toolchain:
  - output: `workspace/private/builds/audio/v2526-acdb-ownprocess-exit-group-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2512`
  - SHA256: `7d3ab2a7d3d59c7d4cbe6db5ccfe0927525f34e7741ba1376db603f3a37b9a33`
  - file: `ELF 32-bit LSB shared object, ARM, EABI5, dynamically linked, interpreter /system/bin/linker`
  - DT_NEEDED closure present: `libacdbloader.so`, `libaudcal.so`, `libdiag.so`, `libacdb-fts.so`, `libacdbrtac.so`, `libadiertac.so`
  - prohibited boundary checks pass: no `dlopen`/`dlsym`, no `/dev/msm_audio_cal`, no `0xC00461CB`, no `tinyplay`/`tinymix`/`AudioTrack`, no Magisk install token.

## Next Unit

- One live rerun is now justified with the V2526 rebuilt helper.
- Expected discriminator:
  - if ACDB still returns `-12`, the host step should return promptly instead of timing out;
  - if it still times out, the hang is not a thread-group exit issue and must be classified from preserved artifacts;
  - if it progresses past init, continue to pure-read `acdb_ioctl` GET capture only.
- Keep all V2490/V2524 boundaries: no HAL injection, no playback, no native speaker write, no native `/dev/msm_audio_cal` SET ioctl, checked rollback to V2321.
