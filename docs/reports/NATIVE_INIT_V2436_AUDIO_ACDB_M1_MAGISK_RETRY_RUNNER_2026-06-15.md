# NATIVE_INIT V2436 — ACDB M1 Magisk Retry Runner Source/Test

Date: 2026-06-15

## Purpose

Implement the source/test-only retry runner for the M1 temporary Magisk module path after
V2435 proved exact create/remove/no-residue under `/data/adb/modules`. This unit does not
boot Android and does not write `/data/adb`; it prepares the next exact-gated live M1 retry.

## Artifacts

Added:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py`
- `tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py`

Future live exact gate:

```text
AUD-5J-acdb-m1-magisk-module-retry go: rollbackable Android AudioTrack speaker msm_audio_cal ioctl payload capture with temporary Magisk service module, corrected su-c staging, exact cleanup, no native calibration ioctl, no native speaker write, rollback to V2321
```

## Design Delta From V2430

V2430 failed while placing the module under `/data/adb/modules`. V2432 and V2435 showed that the
safe working shell form is the remote-shell parsed form:

```text
adb shell "su -c '<script>'"
```

V2436 keeps V2429's private module template and V2430's Android-good measurement purpose, but changes
the staging model:

- use `adb shell "su -c '<script>'"` for staging, install, collection prepare, and cleanup,
- use `adb shell "su -mm -c '<script>'"` for a mount-master read-only module namespace probe,
- preflight-abort if the exact module path or `modules_update` path already exists,
- avoid deleting `/data/adb/modules/...` before the pre-residue check,
- stage only exact files into `/data/adb/modules/a90_audio_acdb_m1_v2429`,
- cleanup exact module files and exact private scratch paths before rollback,
- keep `magisk --install-module` deferred.

## Hard Boundary

The runner remains Android-good measurement packaging only. It does not:

- issue native `/dev/msm_audio_cal` ioctls,
- replay ACDB from native init,
- write native speaker/mixer/PCM state,
- run native `tinymix`/`tinyplay`,
- use `post-fs-data.sh`,
- call `magisk --install-module`,
- touch non-boot partitions.

## Validation

Commands run:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py
PYTHONPATH=tests python3 -m unittest tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py
PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py --dry-run
PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2436.py --dry-run --materialize-module-template --module-out-dir <tmp>
PYTHONPATH=tests python3 -m unittest discover -s tests
git diff --check
```

Focused tests cover:

- V2436 identity and future exact approval phrase,
- corrected remote-shell staging metadata,
- V2435 cleanup discipline metadata,
- materialized dry-run `future_live_ready=true`,
- `su -c` and `su -mm -c` command evidence,
- `A90_M1_RESIDUE_CHECK_OK`, `A90_M1_INSTALL_OK`, and `A90_M1_CLEANUP_OK` evidence,
- rejection of broad `/data/adb/modules` removal and `magisk --install-module`,
- wrong live approval refusing before device action.

Dry-run result before materialization:

```text
run_id=V2436
ok=true
future_live_ready=false
command_safety.ok=true
blocker=V2429 module plan not live-ready: module template not materialized
```

Materialized dry-run result:

```text
run_id=V2436
ok=true
future_live_ready=true
future_live_blockers=[]
command_safety.ok=true
module_ok=true
```

Full test result:

```text
Ran 1185 tests in 25.416s
OK
```

No live Android boot or `/data/adb` write was performed in V2436.

## Next Step

The next meaningful unit is the exact-gated V2437 live M1 retry using the V2436 runner. If it captures
`msm_audio_cal` payload events, analyze command order, decoded headers, private payload hashes,
mem-handle policy, and cleanup behavior before designing native replay. If it still captures zero
events despite confirmed module activation, classify whether the Android-good path has reached a
measurement wall before considering any different Android-side hook.
