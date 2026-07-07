# S22+ — Ramoops DTBO Status-Only Gate Source (2026-07-08)

## Summary

Codex added a narrow DTBO-only status gate helper after the active-DTB
provenance audit proved that stock DTBO overlays are what keep live
`ramoops_region/status` disabled.

Added:

`workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py`

No live flash, reboot, partition write, or ADB read was performed by this unit.

## Purpose

This helper deliberately separates the next observability proof from M13/M18.
It does not accept a boot/native-init candidate path.

Future live flow, once separately authorized:

1. Verify the pinned DTBO candidate and stock DTBO rollback AP.
2. Verify current Android/root, current boot baseline, current stock DTBO hash,
   and current live `ramoops_region/status=disabled`.
3. Flash only the patched DTBO AP.
4. Require Android/root to return.
5. Verify current DTBO hash is the pinned patched DTBO.
6. Verify live `ramoops_region/status=okay`.
7. Restore stock DTBO.
8. Verify current DTBO hash is stock again and live status is back to
   `disabled`.

M13/M18 should remain stopped until this status-only gate proves the retained
console node is actually enabled in the live DT.

## Authorization State

Live is not authorized by this source commit.

The helper reserves a new live token:

`S22PLUS-RAMOOPS-DTBO-STATUS-LIVE-GATE`

The existing `AGENTS.md` DTBO+M18 exception is not reused because it was scoped
to the older M18 capture flow. This status-only gate needs a fresh SHA-pinned
exception whose wording says:

- `S22+ ramoops DTBO status-only`
- candidate DTBO AP SHA256
  `4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00`
- rollback DTBO AP SHA256
  `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`
- patched raw DTBO SHA256
  `1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`
- stock raw DTBO SHA256
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`
- `S22PLUS-RAMOOPS-DTBO-STATUS-LIVE-GATE`
- `S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO`
- `dtbo.img.lz4`
- `ramoops_region/status=okay`
- `restore stock DTBO`
- `no boot candidate`

Until those markers exist, the helper fails before Android/device action.

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
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_status_live_gate.py
```

Observed:

```text
offline-check ok: DTBO status candidate and rollback APs verified; no device action
```

Default execution stopped before device action as intended:

```text
AGENTS.md missing ramoops DTBO status-only authorization markers:
['S22+ ramoops DTBO status-only',
 'S22PLUS-RAMOOPS-DTBO-STATUS-LIVE-GATE',
 'no boot candidate']
```

## Next Step

If the operator wants to run this live, add a narrow status-only `AGENTS.md`
exception with the markers above, then run the default dry-run and only then the
ack-gated live command.
