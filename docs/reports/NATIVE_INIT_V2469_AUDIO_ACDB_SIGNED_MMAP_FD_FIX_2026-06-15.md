# NATIVE_INIT_V2469_AUDIO_ACDB_SIGNED_MMAP_FD_FIX_2026-06-15

## Scope

Host-only fix after V2468.

V2468 proved the Android audio process maps the custom-topology dmabuf with
`mmap2(fd=37, len=4916, prot=0x3, flags=0x1)`, but the fallback read from the
owner mapping failed with errno `5` (`EIO`). It also exposed observer noise:
AArch32 `mmap2` fd `-1` was logged as unsigned `4294967295`, inflating mmap
counts with anonymous mappings.

V2469 fixes only that observer-noise bug. It does not run a device step and
does not issue native `/dev/msm_audio_cal` calibration ioctls.

## Change

`a90_acdb_ioctl_capture_diag_v2449.c` now decodes mmap fd arguments through a
dedicated helper:

```c
static long mmap_fd_arg(const struct syscall_frame *frame) {
    if (!frame || !frame->abi) return -1;
    if (!strcmp(frame->abi, "aarch32")) return (int32_t)((uint32_t)frame->args[4]);
    return (long)frame->args[4];
}
```

`handle_mmap_entry()` uses that signed fd value before its existing
`fd < 0 || length == 0` filter. As a result, AArch32 `mmap2(..., fd=-1, ...)`
is ignored instead of being recorded as fd `4294967295`.

The planner source-state contract and focused tests now assert the signed-fd
filter exists.

## Validation

Host-only validation:

- `python3 -m py_compile`
  - `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py`
  - `tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py`
  - `tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- `aarch64-linux-gnu-gcc -O2 -static -s -Wall -Wextra`
  - output: `workspace/private/builds/audio/v2469-signed-mmap-fd/a90_acdb_ioctl_capture_diag_v2449`
  - `file`: AArch64 static executable
- Focused unittest:
  - `tests.test_native_audio_acdb_m1_diag_observer_planner_v2449`
  - `tests.test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451`
  - result: `18` tests OK
- Materialized private module dry-run:
  - `future_live_ready=true`
  - `future_live_blockers=[]`
  - `command_safety_ok=true`
  - `contains_signed_mmap_fd_filter=true`
  - `helper_ok=true`
  - `module_ok=true`

No flash, Android boot handoff, Magisk module activation, playback, or native
calibration ioctl ran in V2469.

## Next capture method

Do not rerun the unchanged V2467/V2468 live path. It already proved:

- fd `37` is a real dmabuf fd at Android `mmap2()` time;
- the payload-sized mapping exists in the owner process;
- cross-process reads from the mapped VA fail with `EIO`;
- later `/proc/<tgid>/fd/<mem_handle>` open can fail with `ENXIO`.

The next meaningful unit is host-only V2470: implement early dmabuf fd
duplication at `mmap_entry` time.

Proposed V2470 direction:

1. when the observer sees an fd-backed `mmap`/`mmap2` entry whose fd target is a
   dmabuf and whose length is within the private capture limit, immediately open
   `/proc/<fd_pid>/fd/<fd>` and retain a duplicate fd in the helper;
2. attach that duplicate fd to the corresponding successful mmap record;
3. at the later custom-topology SET_CAL edge, use the retained duplicate fd to
   `mmap()` and copy the private payload bytes, instead of reopening
   `/proc/<tgid>/fd/<mem_handle>` after the stock process may have closed it or
   reading the owner VA through `process_vm_readv()` / `PTRACE_PEEKDATA`;
4. keep raw payload bytes private and publish only length/hash metadata.

This remains an Android-good measurement helper path. It must not issue native
calibration ioctls and must not become a native-init runtime dependency.

