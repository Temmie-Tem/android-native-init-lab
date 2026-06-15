# NATIVE_INIT_V2457_AUDIO_ACDB_ROOT_OUTPUT_HARDENING_2026-06-15

## Summary

V2457 is a host-only hardening unit for the V2456 AUD-5L live blocker. V2456
proved the Android handoff and boot-complete recheck could pass, but
`adb shell su -c id` returned rc `0` with empty stdout/stderr. The previous
runner treated that as a generic missing-`uid=0` failure and stopped before
module staging.

This unit updates the shared Android/Magisk ACDB measurement settle logic so an
empty-output Magisk root probe is classified distinctly, retried in a bounded
way, and recorded as metadata. `uid=0` remains the hard gate before any
module staging, late observer, Android `AudioTrack`, or payload collection.

## Changes

- Updated
  `workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py`:
  - added `android_root_recheck_summary()`;
  - classify root probes as:
    - `root-ready`
    - `root-output-empty`
    - `root-command-failed`
    - `root-no-uid0`
  - validate combined stdout/stderr for `uid=0`;
  - record rc, stdout/stderr paths, stdout/stderr lengths, classification, and
    attempt counters;
  - retry the initial post-handoff root check up to four attempts by default,
    with a two-second delay;
  - expose `--android-root-recheck-attempts` and
    `--android-root-recheck-sleep-sec` for controlled future live runs.
- Updated
  `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`:
  - exposes the shared root retry options;
  - reports the root hard-gate contract in dry-run metadata;
  - uses the same root classification metadata for the post-module root retry
    loop.
- Added focused host-only regression tests for empty output, stderr `uid=0`,
  bounded retry, exhausted retry failure, and V2451 dry-run metadata.

## Validation

- `python3 -m py_compile`
  - `workspace/public/src/scripts/revalidation/native_audio_acdb_android_measurement_planner_v2396.py`
  - `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- `PYTHONPATH=tests python3 -m unittest`
  - `tests.test_native_audio_acdb_android_measurement_planner_v2396`
  - `tests.test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451`
  - result: `28` tests passed.
- Materialized V2451 dry-run with the V2457 metadata:
  - `ok=true`
  - `future_live_ready=true`
  - `future_live_blockers=[]`
  - `command_safety_ok=true`
  - initial handoff root attempts: `4`
  - initial handoff root sleep: `2.0s`
  - post-module root attempts: `8`
  - post-module root sleep: `3.0s`
  - helper SHA256:
    `9520e9f297ba4cb52ce2730d8166876409162a70f64998b7c2ac16ca21f165f8`
  - module zip SHA256:
    `6f90d81c4cb03ac62c7174754b4746bb4d329a40eb009131fe2e021ec2b4f7d4`
- `git diff --check` passed.

## Next

The next meaningful unit is a fresh AUD-5L live rerun using the V2457-hardened
runner. The expected discriminator is now narrower:

- if `su -c id` initially returns empty output again, the runner should retry
  and record `root-output-empty` attempts;
- if a retry reports `uid=0`, module staging can proceed;
- if all attempts remain empty/non-root, stop before module staging and roll
  back, with better root probe evidence than V2456.

Do not attempt native ACDB replay until the Android-good payload order, decoded
headers, private payload hashes, mem-handle policy, and cleanup policy are
pinned.

