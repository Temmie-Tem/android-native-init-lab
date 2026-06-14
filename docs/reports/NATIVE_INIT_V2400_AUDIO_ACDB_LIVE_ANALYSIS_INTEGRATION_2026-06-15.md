# NATIVE_INIT V2400 — Audio ACDB live-analysis integration

## Scope

Host-only source/test unit. No Android boot, ADB command, Magisk install, native speaker write,
`/dev/snd` open, mixer write, playback, or ACDB ioctl ran in this unit.

Touched public paths:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py`
- `tests/test_native_audio_acdb_android_measurement_planner_v2396.py`

## Decision

V2400 wires the V2399 analyzer into the exact-gated V2397 live runner. After a future AUD-5A capture
finishes and rollback proof is present, `run_live()` now attaches `post_live_analysis` to
`result.json` by calling the host-only V2399 parser on the run directory.

This removes the manual post-live handoff gap: a successful future AUD-5A run should leave both the raw
private capture and the conservative branch decision in the same private `result.json`.

## Behavior

- Analysis is skipped unless `result.ok=true` and `result.rolled_back=true`.
- Analysis is best-effort: parser errors are recorded as `decision=analysis-error` without changing
  rollback/capture evidence.
- The attached analysis preserves V2399 boundaries: `host_only=true`, `device_action=none`, and raw logs
  remain under `workspace/private`.
- No new live path is opened; the existing exact AUD-5A approval phrase is still required for
  `--run-live`.

## Validation

Commands run:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py \
  workspace/public/src/scripts/revalidation/analyze_audio_acdb_android_measurement_v2399.py \
  tests/test_native_audio_acdb_android_measurement_planner_v2396.py \
  tests/test_analyze_audio_acdb_android_measurement_v2399.py
PYTHONPATH=tests python3 -m unittest \
  tests/test_native_audio_acdb_android_measurement_planner_v2396.py \
  tests/test_analyze_audio_acdb_android_measurement_v2399.py
PYTHONPATH=tests python3 -m unittest discover -s tests
git diff --check
```

Focused unit tests: `17` tests passed across V2396/V2399. Full test suite: `1086` tests passed.

## Next frontier

The next live-capable unit remains exact-gated AUD-5A/V2397. If it completes and rolls back, inspect
`result.json.post_live_analysis.decision` first; it should classify the capture as
`bounded-native-acdb-candidate`, `hal-dependent-or-opaque`, `negative-no-calibration`, or
`capture-incomplete`.
