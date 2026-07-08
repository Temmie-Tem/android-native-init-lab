# S22+ M24 PMSG-Steps Gate Source - 2026-07-08

## Summary

Added a guarded live-gate source for the M24 pmsg-step candidate. This is a
policy-inert source/readiness step only: no flash, reboot, partition write,
sysfs write, or live device action was performed.

M24 keeps the M23 DTS-exact QMP/DWC3 43-module closure, but writes
`A90_STEP:M24:` records to `/dev/pmsg0` before phase transitions and module
insertion calls. The helper is designed to preserve the current manual Download
rollback discipline and then collect retained pmsg/pstore, `/proc/last_kmsg`,
and Samsung reset-context surfaces after rollback.

## Files

- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py`
- Inert exception draft:
  `docs/operations/S22PLUS_M24_PMSG_STEPS_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`
- Tests:
  `tests/test_s22plus_m24_pmsg_steps_live_gate.py`

## Pinned Candidate

- AP SHA256:
  `e09538024abe89585486d54856a5c86bef666da456f314084d4d4d8bb6553fe8`
- boot SHA256:
  `0cccc003687227c4265081fa59d440f4be3e7f40fbb64aca2a3930ca7d5ca3df`
- base boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- kernel SHA256:
  `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- `/init` SHA256:
  `4086d18f453980893fa1b8022f93991775b0ee28a6088f1216de82b74cbaf341`
- module-list SHA256:
  `a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349`
- generated-source SHA256:
  `f9a060f7804571c036631c954b3e88c064aa33176d7d8ec6abe9da8b8bf84bdd`
- vendor DTB SHA256:
  `2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e`

## Gate Behavior

- `--offline-check` verifies the pinned M24 AP, M24 manifest, Magisk rollback
  AP, and stock boot fallback AP without checking `AGENTS.md` and without
  touching a device.
- Default dry-run verifies artifacts, then requires the exact `AGENTS.md`
  authorization markers before Android preflight. With current `AGENTS.md`, it
  fails closed before device access.
- `--live` is unavailable until that exception exists and the explicit ack
  token is supplied:
  `S22PLUS-M24-PMSG-STEPS-LIVE-GATE`.
- `--rollback-from-download` is the attended recovery path after operator
  manual Download entry and requires:
  `S22PLUS-M24-PMSG-STEPS-ROLLBACK-FROM-DOWNLOAD`.
- After rollback and Android/root return, the helper captures:
  - pstore files through `collect_android_pstore()`;
  - `/proc/last_kmsg`;
  - extracted `A90_STEP:M24:` lines into `post_m24_boot_rollback_pmsg_steps.txt`;
  - Samsung reset-context surfaces through `s22plus_reset_reason_readonly_probe`.

Captured reset-context targets include:

```text
/proc/reset_summary
/proc/reset_klog
/proc/reset_history
/proc/reset_tzlog
/proc/enhanced_boot_stat
```

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py \
  tests/test_s22plus_m24_pmsg_steps_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m24_pmsg_steps_live_gate

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m24_pmsg_steps_live_gate.py
```

Results:

- `py_compile`: pass
- unit tests: `Ran 5 tests ... OK`
- offline check: pass, no device action
- default run: expected fail-closed on missing `AGENTS.md` M24 authorization
  markers before Android/device access

## Next Step

If proceeding live, copy the inert exception draft into `AGENTS.md`, rerun
`py_compile`, unit tests, `--offline-check`, and a default dry-run. Then run the
attended live gate only with the exact ack token. If the candidate loops and the
operator manually enters Download mode, run `--rollback-from-download` so the
post-rollback pmsg/pstore/last_kmsg/reset-context capture is not skipped.
