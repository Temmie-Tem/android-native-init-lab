# NATIVE_INIT_V2467_AUDIO_ACDB_DMABUF_MMAP_FALLBACK_2026-06-15

## Scope

Host-only fallback implementation after V2466 proved that the V2463
`/proc/<tgid>/fd/<mem_handle>` duplication method is insufficient for the
Android-good custom-topology ACDB dmabuf payload.

No device action ran in this iteration. No Android boot, Magisk staging,
AudioTrack playback, native `/dev/msm_audio_cal` ioctl, mixer write, PCM write,
or calibration replay was executed.

## Decision

`v2467-dmabuf-mmap-lifecycle-fallback-host-only`

The Android-side diagnostic observer now records traced-process `mmap` lifecycle
events and can use them as a private fallback source when proc-fd duplication
fails at `AUDIO_SET_CALIBRATION`.

This directly targets the V2466 gap:

- V2466 reached Android-good playback and captured four custom-topology
  `AUDIO_SET_CALIBRATION` headers.
- All four had `cal_type=39`, `cal_size=4916`, `mem_handle=35/37`.
- All four failed at opening `/proc/<tgid>/fd/<mem_handle>` with errno `6`.
- No dmabuf binary file or SHA-256 hash was produced.

## Implementation

Touched public files:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_diag_v2449.c`
- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py`
- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_live_handoff_v2450.py`
- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- `tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py`
- `tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`

The helper now:

1. decodes the first six syscall arguments for AArch64 and AArch32 tracees;
2. recognizes AArch64 `mmap` and AArch32 `mmap2` (`A90_COMPAT_ARM_NR_MMAP2=192`);
3. records `mmap_entry` / `mmap_exit` JSONL events with fd, length, prot, flags,
   offset, return address, and fd target;
4. keeps a bounded ring of recent successful mappings keyed by fd;
5. when a custom-topology SET_CAL header is seen and proc-fd open fails, looks
   up a recent mapping for the same `mem_handle` fd and declared length;
6. copies the declared payload bytes from traced process memory via the existing
   private `read_remote()` path and writes only private `dmabuf-*-remote-map.bin`
   artifacts.

New capture statuses include:

- `ok-remote-mmap`
- `remote-mmap-write-short`
- `open-proc-fd-failed-no-mmap-record`
- `open-proc-fd-failed-remote-mmap-read-failed`

The existing proc-fd + direct `mmap()` path remains first choice. The new
remote-mmap fallback only runs after that path fails.

## Safety boundaries

Unchanged:

- helper does not open `/dev/msm_audio_cal`;
- helper does not issue `AUDIO_SET_CALIBRATION` or any calibration ioctl;
- helper does not run playback, `tinymix`, `tinyplay`, DHCP, routes, or Wi-Fi;
- raw dmabuf bytes remain private-only and summaries expose only size/SHA-256;
- native replay remains blocked until Android-good payload bytes, hash,
  lifetime, and cleanup policy are pinned.

This is still measurement infrastructure, not native runtime behavior.

## Validation

Static validation passed:

```text
aarch64-linux-gnu-gcc -O2 -static -s -Wall -Wextra \
  -o workspace/private/builds/audio/v2467-compile-check/a90_acdb_ioctl_capture_diag_v2449 \
  workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_diag_v2449.c

file workspace/private/builds/audio/v2467-compile-check/a90_acdb_ioctl_capture_diag_v2449
# ELF 64-bit LSB executable, ARM aarch64, statically linked
```

Focused Python validation passed:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_planner_v2449.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_diag_observer_live_handoff_v2450.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py \
  tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py \
  tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest \
    tests/test_native_audio_acdb_m1_diag_observer_planner_v2449.py \
    tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py
# Ran 18 tests — OK

python3 -m unittest discover -s tests -p 'test_*.py'
# Ran 1250 tests — OK
```

Materialized private module dry-run passed under
`workspace/private/builds/audio/v2467-mmap-fallback-module/`:

```json
{
  "ok": true,
  "future_live_ready": true,
  "future_live_blockers": [],
  "command_safety_ok": true,
  "source_mmap_lifecycle": true,
  "source_remote_mmap_fallback": true,
  "module_ok": true,
  "helper_ok": true
}
```

## Next safe unit

Run one fresh bounded Android-good dmabuf capture rerun using the V2467
mmap-lifecycle fallback helper.

Expected discriminator:

1. `ok-remote-mmap` plus a dmabuf SHA-256 appears: payload capture gate is
   solved; decode/hash privately before any native replay design.
2. `open-proc-fd-failed-no-mmap-record`: helper started too late for the mmap
   edge or the payload is not userspace-mapped at SET_CAL time; consider a
   narrower earlier observer only after confirming the new mmap counters.
3. `remote-mmap-read-failed` or short read: mapping exists but process-memory
   read policy/timing still blocks capture; pivot to fdinfo/maps timing evidence.

Do not issue native `/dev/msm_audio_cal` calibration ioctls in the next unit.
