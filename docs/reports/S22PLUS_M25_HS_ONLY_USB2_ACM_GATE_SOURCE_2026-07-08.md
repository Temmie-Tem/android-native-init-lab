# S22+ M25 HS-Only USB2 ACM Gate Source - 2026-07-08

## Summary

Added a guarded M25 live-gate source for the HS-only USB2 ACM fault-avoidance
candidate. This is a host-side readiness step only: no flash, reboot, partition
write, sysfs write, or live device action was performed by this gate-source
unit.

The gate is intentionally policy-inert until a SHA-pinned exception is copied
into `AGENTS.md`.

## Files

- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py`
- Inert exception draft:
  `docs/operations/S22PLUS_M25_HS_ONLY_USB2_ACM_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`
- Tests:
  `tests/test_s22plus_m25_hs_only_usb2_acm_live_gate.py`

## Pinned Artifacts

- M25 boot AP SHA256:
  `7f89cfb8ff188190d1d161aee97e3edec2730bfc46efca9df37f2035f7206805`
- M25 boot image SHA256:
  `0ace02ff82be1cb7473879ff52f1c9e8d1491edaa3d9a88b829f901b2c86559f`
- M25 `/init` SHA256:
  `cc03d95f06b851717d3ccb4fc32fbecac3adfe7109c1a68454f846e3014ecf75`
- M25 module-list SHA256:
  `00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496`
- M25 generated-source SHA256:
  `22350e7de748cf3a2f47236ef984bb224df58ffa7664ced811151c9db189562f`
- M25 DTBO candidate AP SHA256:
  `35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6`
- M25 patched raw DTBO SHA256:
  `8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17`
- M25 stock DTBO rollback AP SHA256:
  `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`

## Gate Behavior

- `--offline-check` verifies the pinned M25 boot AP, DTBO candidate AP, stock
  DTBO rollback AP, M25 manifest, Magisk rollback AP, and stock boot fallback
  AP without checking `AGENTS.md` and without touching a device.
- Default dry-run verifies artifacts, then requires the exact `AGENTS.md`
  authorization markers before Android preflight. With current `AGENTS.md`, it
  fails closed before device access.
- `--live` is unavailable until that exception exists and the explicit ack token
  is supplied:
  `S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE`.
- `--rollback-from-download` is the attended recovery path after operator manual
  Download entry and requires:
  `S22PLUS-M25-HS-ONLY-ROLLBACK-FROM-DOWNLOAD`.
- `--restore-dtbo-from-download` and `--restore-dtbo-from-android` restore only
  the pinned stock DTBO AP and require:
  `S22PLUS-M25-RESTORE-STOCK-DTBO`.

The live path is two-stage: flash DTBO high-speed cap, verify Android/root and
patched DTBO hash, then flash the M25 boot AP. Rollback restores Magisk boot
first and then stock DTBO.

## Current Device Recheck

After the operator reported bootloop/manual Download-mode entry, the current
host view was rechecked before any rollback. The device was already back on
Android ADB, not Download mode:

```text
boot_completed=1
verifiedbootstate=orange
boot_recovery=0
su uid=0(root)
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo        97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

No rollback was needed or performed.

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
- unit tests: `Ran 5 tests ... OK`
- offline check: pass, no device action
- default run: expected fail-closed on missing `AGENTS.md` M25 authorization
  markers before Android/device access

## Next Step

If proceeding live, copy the inert exception draft into `AGENTS.md`, re-run the
dry-run, then run the attended live gate only with the exact ack token. If the
candidate loops and the operator manually enters Download mode, immediately run
`--rollback-from-download` to restore Magisk boot and stock DTBO.
