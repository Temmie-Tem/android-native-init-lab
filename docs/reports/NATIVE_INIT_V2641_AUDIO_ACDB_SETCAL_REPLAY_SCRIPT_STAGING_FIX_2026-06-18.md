# NATIVE_INIT V2641 — ACDB SET-cal replay script staging fix

Date: 2026-06-18

## Scope

Host-only fix for the V2640 invalid live run. The previous V2639 runner inlined a
multi-kilobyte `start_and_wait_all_set` shell body through serial `cmdv1x`; the
serial protocol split/corrupted the payload and the device reported
`[err] unknown command: ...` before ACDB SET replay could be trusted.

## Change

- V2638 now records remote script paths for the replay start, deallocate check,
  and runtime cleanup scripts.
- V2639 now materializes those long shell bodies as run-local files, transfers
  them under the existing remote replay directory, and executes only short
  commands of the form `/bin/busybox sh <remote-script>`.
- V2639 marks protocol noise or `unknown command` output as a hard failure before
  PCM probing.

## Safety

No device action was run in this host-only fix. No ACDB payload bytes, compiled
binaries, or raw private logs are committed.

## Validation

- `python3 -m py_compile` for the V2638/V2639 scripts and focused tests.
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_runner_plan_v2638 tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- Regenerated V2638/V2639 reports with script-file staging metadata.
- `git diff --check`

## Next Unit

Rerun V2639 live once with the staged-script transport fix. Success criteria for
that rerun: the start script must produce a trustworthy final SET marker, helper
cleanup must show `A90_ACDB_SETCAL_REPLAY_DONE rc=0` plus reverse deallocate
markers, and only then should PCM/dmesg be interpreted as a real SET replay
result.
