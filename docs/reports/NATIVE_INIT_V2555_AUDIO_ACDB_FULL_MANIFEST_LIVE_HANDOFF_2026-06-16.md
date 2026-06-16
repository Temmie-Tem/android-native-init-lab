# NATIVE_INIT V2555 — ACDB full-manifest live handoff

Date: 2026-06-16

## Scope

Android own-process ACDB capture handoff using the V2490 checked Android boot/stage/pull/rollback engine and the V2553 manual-arm helper/preload artifacts.

## Result

- decision: `v2555-ownprocess-helper-sigsegv-no-events-rollback-pass`
- ok: `False`
- out_dir: `workspace/private/runs/audio/v2555-acdb-full-manifest-20260616-095409`
- classification: `v2555-ownprocess-helper-sigsegv-no-events`
- topology_success_count: `0`
- per_device_success_count: `0`
- successful_nonzero_count: `0`
- real_audio_set_pass_through_count: `0`

Raw ACDB buffers remain private under the run directory and are not committed.

## Live Evidence

- Android handoff, staging, artifact pull, cleanup, and checked rollback completed.
- Final native V2321 selftest after rollback: `fail=0`.
- V2553 helper SHA was staged even though the remote filename came from the reused V2490 engine:
  `d93bbeb645dbb48f34f50451338058ce5c8b5648ee707aea889fcd03cd795406`.
- V2553 manual-arm preload SHA was staged:
  `a271fcda7260e0175a19cb0b3ed0c7c505b2835a018522ddfe536afe64c1db36`.
- `ioctl()` interposition was active:
  - `AUDIO_ALLOCATE_CALIBRATION`: 26 fake-success records.
  - `AUDIO_DEALLOCATE_CALIBRATION`: 1 fake-success record.
  - `AUDIO_SET_CALIBRATION`: 1 fake-success record.
  - real `AUDIO_SET_CALIBRATION` pass-through: `0`.
- Helper rc: `139` / `Segmentation fault`.
- `acdbtap` rows: `0`; `acdbtap` call rows: `0`; no topology or per-device raw buffers were captured.

## Root-Cause Update

The live logs contradict the V2554 assumption that the helper can arm capture
after `acdb_loader_init_v3()` returns:

```text
ACDB -> ACDB_CMD_INITIALIZE_V2
ACDB -> ADIE RTAC INIT
ACDB -> send_common_custom_topology
ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_SIZE_V3
ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_V3: size:0x1334 ret=0
ACDB -> CORE_CUSTOM_TOPOLOGIES
```

Those lines occur before any helper-side event file is written, so
`acdb_loader_init_v3()` is internally driving `send_common_custom_topology()` and
then crashing before it returns to the helper. Therefore `a90_arm_capture()`
after `init_v3` is too late: the target GET already happened.

The important positive result is that fake allocation moved the process through
the topology path and the direct `AUDIO_SET_CALIBRATION` was suppressed. The
remaining capture bug is the arming point, not the allocation/SET boundary.

## Artifacts

- helper_sha256: `d93bbeb645dbb48f34f50451338058ce5c8b5648ee707aea889fcd03cd795406`
- preload_sha256: `a271fcda7260e0175a19cb0b3ed0c7c505b2835a018522ddfe536afe64c1db36`

## Next Unit

V2556 should restore a safe post-initialize auto-arm inside the `acdb_ioctl`
wrapper:

1. while unarmed, call the real `acdb_ioctl` with no dump/file I/O/hash;
2. if that silent call is `ACDB_CMD_INITIALIZE_V2` and returns `0`, set
   `a90_armed=1`;
3. dump subsequent `acdb_ioctl` calls, including the `send_common_custom_topology`
   calls that happen inside `init_v3`;
4. keep `A90_ACDBTAP_EXIT_ON_TARGET=0` for full-manifest capture;
5. rerun the same V2555 handoff and preserve all ordered records privately.
