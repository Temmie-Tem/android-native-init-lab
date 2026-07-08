# S22+ M25 HS-Only USB2 ACM Pre-Live Hardening - 2026-07-08

## Summary

PASS: tightened the M25 live helper before any live flash. No live flash,
reboot, partition write, sysfs write, or rollback was performed.

The hardening fixes one rollback accounting bug and one timeline ambiguity:

- Stock boot fallback is now treated as a valid fallback path instead of being
  forced through a Magisk-root-only boot hash read.
- `rollback_boot_ready` now marks Android return after boot rollback, while
  stock DTBO restore uses a separate `dtbo_rollback_boot_ready` event.

## Changed Files

- `workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py`
- `tests/test_s22plus_m25_hs_only_usb2_acm_live_gate.py`

## Rationale

M25 normally rolls back through the pinned Magisk boot AP. The helper also
allows a stock boot fallback if Magisk rollback transfer fails or if the
operator explicitly selects stock rollback. The previous code always tried to
verify the boot partition through `su -c dd` against the Magisk boot hash after
Android returned. That is correct for Magisk rollback, but wrong for stock
fallback because stock Android is not expected to have Magisk root.

The patched behavior is:

- Magisk rollback: verify `boot` equals
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
- Stock rollback: skip the root-required boot hash read and log
  `boot_restore_hash_check=skipped rollback_target=stock root_not_expected=1`.

The timeline change keeps boot rollback readiness separate from DTBO rollback
readiness:

```text
rollback_flash_start
rollback_flash_done
rollback_boot_ready
dtbo_rollback_flash_start
dtbo_rollback_flash_done
dtbo_rollback_boot_ready
live_session_end
```

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  tests/test_s22plus_m25_hs_only_usb2_acm_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m25_hs_only_usb2_acm_live_gate

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py
```

Results:

- `py_compile`: pass
- unit tests: `Ran 7 tests ... OK`
- `--offline-check`: pass, no device action
- default dry-run: pass, no flash/reboot/write

Dry-run log:

```text
workspace/private/runs/s22plus_m25_hs_only_usb2_acm_live_gate_20260708T120351Z/s22plus_m25_hs_only_usb2_acm_live_gate.txt
```

## Next Step

M25 remains live-capable but not yet executed. The attended live gate still
requires:

```text
--live --ack S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE
```
