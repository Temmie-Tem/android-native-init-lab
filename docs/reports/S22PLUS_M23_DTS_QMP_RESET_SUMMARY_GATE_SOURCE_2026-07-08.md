# S22+ M23 DTS-QMP Reset-Summary Gate Source - 2026-07-08

## Summary

Added a guarded live-gate source for the next M23 DTS-exact QMP/DWC3 run that
captures Samsung reset-context surfaces after rollback.  This is a host-side
readiness step only: no flash, reboot, partition write, sysfs write, or live
device action was performed.

The gate is intentionally policy-inert until a SHA-pinned exception is copied
into `AGENTS.md`.

## Files

- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py`
- Inert exception draft:
  `docs/operations/S22PLUS_M23_DTS_QMP_RESET_SUMMARY_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`
- Tests:
  `tests/test_s22plus_m23_dts_qmp_reset_summary_live_gate.py`

## Pinned Candidate

- AP SHA256:
  `558eddb4b78b68c86d65f171072145c63210e9b33b5d0b56f2a3e4a00f0ba2d8`
- boot SHA256:
  `277bf33c0f7cc62fe2b635b83c22b052d35a4e97dfb2e1cadaf60fdcb961184e`
- base boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- kernel SHA256:
  `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- `/init` SHA256:
  `745131e23a657905542697cc1c0573a87e484df2e9a06810344d8d4d0be6f357`
- module-list SHA256:
  `a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349`
- generated-source SHA256:
  `75610dbd2148017708300aaf5c37b169d12a6a87ec30ed5d96e753708654c9c0`
- vendor DTB SHA256:
  `2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e`

## Gate Behavior

- `--offline-check` verifies the pinned M23 AP, M23 manifest, Magisk rollback
  AP, and stock boot fallback AP without checking `AGENTS.md` and without
  touching a device.
- Default dry-run verifies artifacts, then requires the exact `AGENTS.md`
  authorization markers before Android preflight.  With current `AGENTS.md`,
  it fails closed before device access.
- `--live` is unavailable until that exception exists and the explicit ack
  token is supplied:
  `S22PLUS-M23-DTS-QMP-RESET-SUMMARY-LIVE-GATE`.
- `--rollback-from-download` is the attended recovery path after operator
  manual Download entry and requires:
  `S22PLUS-M23-DTS-QMP-ROLLBACK-FROM-DOWNLOAD`.
- After rollback and Android/root return, the helper captures both legacy
  retained surfaces and Samsung reset-context surfaces through
  `s22plus_reset_reason_readonly_probe.collect()`.

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
  workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py \
  tests/test_s22plus_m23_dts_qmp_reset_summary_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m23_dts_qmp_reset_summary_live_gate

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m23_dts_exact_qmp_reset_summary_live_gate.py
```

Results:

- `py_compile`: pass
- unit tests: `Ran 4 tests ... OK`
- offline check: pass, no device action
- default run: expected fail-closed on missing `AGENTS.md` M23 authorization
  markers before Android/device access

## Next Step

If proceeding live, copy the inert exception draft into `AGENTS.md`, re-run the
dry-run, then run the attended live gate only with the exact ack token.  If the
candidate loops and the operator manually enters Download mode, run
`--rollback-from-download` so the post-rollback reset-context capture is not
skipped.
