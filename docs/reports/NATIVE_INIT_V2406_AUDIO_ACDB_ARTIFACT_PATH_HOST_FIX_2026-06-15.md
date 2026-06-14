# V2406 — AUD-5A Android/Magisk artifact path host fix

Date: 2026-06-15  
Scope: host-only fix for the V2405 Android `/cache` artifact-path blocker  
Device action: none

## Decision

`aud5a-m0-artifact-path-host-validated`

V2405 proved Android/Magisk root was working but failed before staging because the M0 transient
observer used `/cache/a90-audio-acdb-v2396` for artifacts. V2406 removes that `/cache` dependency
from the live runner and generated Magisk-style helper files.

The M0 artifact directory now lives inside the already staged writable tree:

```text
/data/local/tmp/a90-audio-acdb-v2396/artifacts
```

## Code changes

- `REMOTE_ARTIFACT_DIR` now resolves to `/data/local/tmp/a90-audio-acdb-v2396/artifacts`.
- `stage-0` creates and chmods only the `/data/local/tmp` staging tree.
- Generated `a90_acdb_probe.sh` uses `A90_V2396_OUT`, defaulting to the new artifact directory.
- Generated `service.sh` creates the new artifact directory before redirecting `service.log`.
- `baseline`/`active`/`post` probes pass `A90_V2396_OUT` explicitly.
- `collect_private_artifacts`, cleanup, and optional strace output now use the new path.
- Tests assert the dry-run plan and generated module files contain no `/cache/a90-audio-acdb-v2396`.

## Magisk strategy impact

No escalation to M1 is justified by V2405. The failed edge was a bad M0 artifact path, not an early
boot timing miss. M0 remains the default transient helper; M1 temporary boot module still requires a
new exact gate and evidence that M0 misses early ACDB/App Type work.

## Validation

Host-only validation passed:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py tests/test_native_audio_acdb_android_measurement_planner_v2396.py
python3 -m unittest discover -s tests -p 'test_native_audio_acdb_android_measurement_planner_v2396.py'  # 15 passed
python3 -m unittest discover -s tests -p 'test_*.py'  # 1089 passed
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py --dry-run --materialize-module-template
```

Dry-run summary:

```json
{
  "ok": true,
  "future_live_ready": true,
  "future_live_blockers": [],
  "command_safety_ok": true,
  "remote_artifact_dir_in_commands": true,
  "cache_path_in_commands": false,
  "cache_path_in_module": false,
  "collect_private_artifacts": [
    "adb",
    "pull",
    "/data/local/tmp/a90-audio-acdb-v2396/artifacts",
    "<private-run-dir>/device-artifacts"
  ]
}
```

`git diff --check` passed.

## Next step

A fresh bounded AUD-5A live rerun is now unblocked from both known handoff/staging blockers:

- V2404 fixed and live-validated the Magisk root recheck;
- V2406 removes the V2405 `/cache` artifact-path blocker.

The next live run should proceed as the same M0 transient-helper measurement and then feed the
private artifacts into the V2399 analyzer if capture plus rollback both succeed.
