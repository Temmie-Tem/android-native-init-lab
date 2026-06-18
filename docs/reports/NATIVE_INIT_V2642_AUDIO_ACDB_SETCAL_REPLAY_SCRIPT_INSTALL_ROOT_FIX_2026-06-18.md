# NATIVE_INIT V2642 — ACDB SET-cal replay script install-root fix

Date: 2026-06-18

## Scope

Host-only fix for the V2641 staged-script rerun. The long script body was no
longer inlined through serial, but the remote script files were staged under
`/cache/a90-acdb-setcal-replay-v2636/`, which `tcpctl_host install` deliberately
rejects because it is outside the approved helper roots.

## Change

- Remote replay scripts now stage under the allowed root
  `/cache/a90-runtime/bin/v2639-setcal-replay-scripts/`.
- The runtime cleanup script removes both the ACDB replay data directory and the
  staged script directory.
- `install_artifact()` now treats a host command `rc != 0` as install failure even
  if the surrounding step object has `ok=True`, preventing another silent script
  install miss.

## Safety

No device action was run for this fix. No ACDB payload bytes, compiled binaries,
or raw private logs are committed.

## Validation

- `python3 -m py_compile` for V2638/V2639 scripts and focused tests.
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_runner_plan_v2638 tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- Regenerated V2638/V2639 reports.
- `git diff --check`

## Next Unit

Rerun V2639 live once. The next rerun should verify script install under the
allowed root, then require the final SET marker and deallocate markers before PCM
is interpreted.
