# V2421 — Audio ACDB Clone-Follow Observer Host Checkpoint

Date: 2026-06-15  
Scope: host-only implementation, build, dry-run validation. No Android boot, no native-init flash, no playback, no `/dev/msm_audio_cal` open/ioctl from native init.

## Why

V2420 proved the Android-good speaker ACDB/App Type edge still occurs, and the dynamic M0 watcher eventually attached the audio HAL worker TID, but only after the first `/dev/msm_audio_cal` ioctl window had likely passed. Repackaging the same polling watcher as a Magisk boot module would preserve the race. The next useful unit was therefore a clone-following observer that attaches to the audio process before playback and stops newly-created worker threads at birth.

## Implemented

- Added `workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_clone_v2421.c`.
  - Uses `PTRACE_ATTACH` on the process and `PTRACE_O_TRACECLONE` / `PTRACE_GETEVENTMSG` to follow new worker TIDs.
  - Filters syscall stops for `__NR_ioctl` and only records fds resolving to `/dev/msm_audio_cal` through the process fd table.
  - Copies bounded request bytes with `process_vm_readv` fallback to `PTRACE_PEEKDATA` into private JSONL.
  - Does not open `/dev/msm_audio_cal` and does not issue calibration ioctls.
- Added `workspace/public/src/scripts/revalidation/native_audio_acdb_clone_follow_planner_v2421.py`.
  - Builds the helper as a private static AArch64 binary under `workspace/private/builds/audio/v2421-acdb-clone-follow-helper/`.
  - Generates an Android-side controller that starts one clone-following helper per audio process, not one polling helper per existing TID.
  - Emits a future V2422 checked Android/Magisk-root handoff plan with V2321 rollback.
- Added `tests/test_native_audio_acdb_clone_follow_planner_v2421.py`.

## Magisk Direction

The Wi-Fi precedent remains the right model: use Android/Magisk only as a stock-good measurement capsule, then port only bounded reviewed facts into native init.

For this ACDB edge, the delivery tiers are now fixed as:

1. **M0 clone-following transient helper** — default. Stage the helper under `/data/local/tmp`, run it through Magisk `su`, attach before playback, and follow worker creation with `PTRACE_O_TRACECLONE`.
2. **M1 temporary boot module** — fallback only. If M0 cannot attach early enough after Android handoff or must exist before the audio HAL process starts, package the same clone-following observer in a temporary Magisk `service.sh`/optional `post-fs-data.sh`. M1 changes delivery timing only; it must not revert to polling-only semantics.
3. **M2 vendor wrapper** — deferred unless both M0 and M1 fail to expose one identified payload edge.

No tier makes Magisk a native-init runtime dependency. No persistent Magisk module is installed by default, no vendor partition is written, and rollback/cleanup removes Android-side scratch state.

## Dry-Run / Build Result

Materialized dry-run summary:

```json
{
  "ok": true,
  "future_live_ready": true,
  "blockers": [],
  "source_ok": true,
  "build_ok": true,
  "aarch64_static": true,
  "command_safety_ok": true,
  "default_magisk_tier": "M0-clone-following-transient-helper",
  "persistent_install": false
}
```

Private helper binary check:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
```

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_clone_follow_planner_v2421.py tests/test_native_audio_acdb_clone_follow_planner_v2421.py` — pass.
- `python3 -m unittest discover -s tests -p 'test_native_audio_acdb_clone_follow_planner_v2421.py' -v` — 6 tests pass.
- `python3 workspace/public/src/scripts/revalidation/native_audio_acdb_clone_follow_planner_v2421.py --dry-run --materialize-capture-helper` — pass; private static helper built; future live plan ready.

## Next

V2422 should be the exact-gated Android live rerun using the V2421 clone-following observer. If that still misses the ACDB payload edge, evaluate M1 as a temporary Magisk boot-module packaging of the same clone-following helper, not as a polling watcher escalation.
