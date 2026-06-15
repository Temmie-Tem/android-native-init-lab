# NATIVE_INIT_V2470_AUDIO_ACDB_EARLY_DMABUF_FD_DUP_2026-06-15

## Scope

Host-only implementation of the next ACDB dmabuf capture discriminator.

V2468 proved the custom-topology dmabuf fd is alive and mapped during Android
`mmap2()`, but later `/proc/<tgid>/fd/<mem_handle>` open failed with `ENXIO` and
cross-process reads from the owner VA failed with `EIO`. V2469 fixed signed fd
noise so anonymous `mmap2(fd=-1)` records are no longer tracked.

V2470 changes the Android-good observer strategy: duplicate the dmabuf fd at
`mmap_entry` time while the stock audio process still holds it, then use that
retained duplicate at the later SET_CAL edge.

No device step ran in V2470.

## Implementation

The Android-side diagnostic helper now:

1. decodes mmap fd arguments through the V2469 signed-fd helper;
2. resolves the fd target at `mmap`/`mmap2` entry;
3. if capture is enabled, the target name contains `dmabuf`, and the mapping
   length is within the private capture cap, opens `/proc/<fd_pid>/fd/<fd>`
   immediately and stores a duplicate fd in the pending mmap record;
4. transfers that duplicate fd into the successful mmap ring record;
5. closes duplicate fds on ring overwrite, syscall error, tracee exit, and
   helper shutdown;
6. if later proc-fd open fails at custom-topology SET_CAL time, tries the
   retained duplicate fd before falling back to owner-VA reads.

New private payload statuses include:

- `ok-early-dup`
- `early-dup-write-short`
- `open-proc-fd-failed-early-dup-mmap-failed`
- `open-proc-fd-failed-early-dup-output-open-failed`

Mmap telemetry now records `dup_fd` and `dup_errno` in `mmap_entry` /
`mmap_exit` events, and the live-run summarizer preserves those fields in
sampled mmap events.

## Safety boundary

V2470 remains a measurement-only Android-good helper path:

- it does not open `/dev/msm_audio_cal`;
- it does not issue any calibration ioctl;
- it does not run native speaker playback;
- it does not make Magisk a native-init runtime dependency;
- raw dmabuf bytes, if captured in a future live run, remain private artifacts.

The helper only duplicates a dmabuf fd that the stock Android audio process has
already opened and mapped during known-good framework playback.

## Validation

Host-only validation:

- AArch64 static helper build:
  - `aarch64-linux-gnu-gcc -O2 -static -s -Wall -Wextra`
  - output: `workspace/private/builds/audio/v2470-early-dmabuf-dup/a90_acdb_ioctl_capture_diag_v2449`
  - `file`: AArch64 static executable
- `python3 -m py_compile`
  - V2449 planner
  - V2451 live handoff
  - focused ACDB observer tests
- Focused unittest:
  - `tests.test_native_audio_acdb_m1_diag_observer_planner_v2449`
  - `tests.test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451`
  - result: `18` tests OK
- Materialized private module dry-run:
  - `future_live_ready=true`
  - `future_live_blockers=[]`
  - `command_safety_ok=true`
  - `contains_signed_mmap_fd_filter=true`
  - `contains_early_dmabuf_fd_duplication=true`
  - `helper_ok=true`
  - `module_ok=true`

## Next safe unit

Next meaningful unit is one fresh bounded Android-good live rerun using the
V2470 helper.

Expected discriminator:

- `ok-early-dup` plus a private `dmabuf-*-early-dup.bin` artifact means the
  payload byte gap is closed and native ACDB replay design can proceed to
  decoded header/order/hash policy.
- `open-proc-fd-failed-early-dup-mmap-failed` means retaining the fd works but
  helper-side dmabuf mmap is not permitted; the next design should move capture
  earlier into the Android owner process path.
- no early-dup attempt means the fd target/lifetime assumption is wrong and the
  mmap-entry evidence must be rechecked.

Native `/dev/msm_audio_cal` calibration ioctls remain blocked.

