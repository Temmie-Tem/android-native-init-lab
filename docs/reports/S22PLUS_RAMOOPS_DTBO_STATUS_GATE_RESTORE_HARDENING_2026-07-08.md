# S22+ — Ramoops DTBO Status Gate Restore Hardening (2026-07-08)

## Summary

Codex hardened the DTBO status-only live gate before running it live. No live
flash, reboot, or partition write was performed by this unit.

Updated helper:

`workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py`

## Issue

The status-only gate already restored stock DTBO on the success path. However,
after a patched DTBO flash and Android/root return, the helper verified:

1. current DTBO hash is the pinned patched DTBO;
2. live `ramoops_region/status=okay`.

If either verification raised, the helper would exit immediately and could leave
the patched DTBO installed even though Android was alive and able to reboot into
Download mode.

## Fix

The patched-Android verification block now catches verification failure, logs
the reason, reboots Android to Download mode, flashes the pinned stock DTBO
rollback AP, verifies Android/root returns, verifies stock DTBO hash, verifies
live status is back to `disabled`, and exits nonzero.

This preserves the failure signal while attempting to leave the device back on
the clean stock-DTBO baseline.

At this point, Android-timeout recovery was still manual-only. The follow-up
hardening below removes that gap when the device exposes a Download/Odin
endpoint.

## Follow-Up Hardening

Codex then removed one more manual-only gap. If Android/root does not return
after the patched DTBO flash, the helper now checks for a Download/Odin endpoint.
If one appears, it automatically flashes the pinned stock DTBO rollback AP and
verifies Android/root, stock DTBO hash, and live `status=disabled` before
returning nonzero.

Manual Download-mode recovery is now required only when neither Android/root nor
an Odin endpoint appears after the patched DTBO flash.

## Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py

PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py \
  --offline-check

PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py \
  --serial <redacted>

PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py \
  --restore-dtbo-from-android \
  --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO \
  --serial <redacted>
```

Observed:

```text
offline-check ok: DTBO status candidate and rollback APs verified; no device action
dry-run ok: DTBO status candidate, rollback AP, AGENTS exception, Android stability, boot hash, stock DTBO hash, and live disabled status verified
stock DTBO restore-from-android already stock
```

All validation above was read-only or stock-state no-op. No live flash, reboot,
or write was performed.

Additional validation after the Android-timeout restore hardening repeated the
same `py_compile`, `--offline-check`, read-only default dry-run, and stock-state
restore no-op checks successfully.
