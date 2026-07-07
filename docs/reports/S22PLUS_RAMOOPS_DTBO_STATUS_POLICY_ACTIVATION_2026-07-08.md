# S22+ — Ramoops DTBO Status-Only Policy Activation (2026-07-08)

## Summary

Codex added the narrow `AGENTS.md` exception for the DTBO-only status gate and
ran the read-only default dry-run. No live flash, reboot, or partition write was
performed.

Helper:

`workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py`

Reserved live ack token:

`S22PLUS-RAMOOPS-DTBO-STATUS-LIVE-GATE`

## Scope

The exception authorizes one future attended status-only live gate:

1. Flash the pinned patched `dtbo` AP.
2. Require Android/root to return.
3. Require the current DTBO hash to match the pinned patched DTBO.
4. Require live `/proc/device-tree/reserved-memory/ramoops_region/status=okay`.
5. Restore stock DTBO using the pinned rollback AP.
6. Require stock DTBO hash and live status back to `disabled`.

It explicitly does not authorize any boot/native-init candidate. M13, M15, M18,
QMP variants, `boot`, `vendor_boot`, recovery, vbmeta, raw `dd`, fastboot, and
additional DTBO candidates remain out of scope.

## Pinned Artifacts

```text
patched DTBO AP.tar.md5
4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00

stock DTBO rollback AP.tar.md5
6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa

patched raw DTBO
1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab

stock raw DTBO
97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
```

Both DTBO APs must contain exactly one member:

```text
dtbo.img.lz4
```

## Validation

Commands run:

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
```

Observed:

```text
offline-check ok: DTBO status candidate and rollback APs verified; no device action
```

Default dry-run passed:

```text
dry-run ok: DTBO status candidate, rollback AP, AGENTS exception, Android
stability, boot hash, stock DTBO hash, and live disabled status verified
```

The default dry-run verified:

- Android/root stability.
- Current known-booting Magisk boot hash.
- Current stock DTBO hash.
- Live `ramoops_region/status=disabled`.

It did not flash, reboot, or write anything.

## Next Step

The next live step is still not automatic. It requires explicit attended
operator approval and the live ack token:

```sh
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py \
  --live \
  --ack S22PLUS-RAMOOPS-DTBO-STATUS-LIVE-GATE \
  --serial <redacted>
```
