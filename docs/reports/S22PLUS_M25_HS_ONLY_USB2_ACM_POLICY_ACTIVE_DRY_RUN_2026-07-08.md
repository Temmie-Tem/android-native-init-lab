# S22+ M25 HS-Only USB2 ACM Policy Active Dry-Run - 2026-07-08

## Summary

PASS: the SHA-pinned M25 boot+DTBO live gate is now active in `AGENTS.md`, and
the guarded dry-run passes. No live flash, reboot, partition write, sysfs write,
or rollback was performed.

This moves M25 from policy-inert to live-capable, but live execution still
requires the explicit live ack token:

```text
S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE
```

## Files

- Active policy:
  `AGENTS.md`
- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py`
- Inert source draft retained for audit:
  `docs/operations/S22PLUS_M25_HS_ONLY_USB2_ACM_AGENTS_EXCEPTION_DRAFT_2026-07-08.md`
- Previous gate-source report:
  `docs/reports/S22PLUS_M25_HS_ONLY_USB2_ACM_GATE_SOURCE_2026-07-08.md`

## Dry-Run Command

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py
```

Result:

```text
dry-run ok: M25 boot/DTBO candidates, rollback APs, AGENTS exception, Android stability, boot/vendor_boot/stock-DTBO hashes verified
```

Run log:

```text
workspace/private/runs/s22plus_m25_hs_only_usb2_acm_live_gate_20260708T115704Z/s22plus_m25_hs_only_usb2_acm_live_gate.txt
```

## Evidence

Policy gate:

```text
agents_exception_missing=[]
```

Artifact pins:

```text
m25_boot_candidate_sha256=7f89cfb8ff188190d1d161aee97e3edec2730bfc46efca9df37f2035f7206805
m25_boot_candidate_members=['boot.img.lz4']
m25_dtbo_candidate_sha256=35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6
m25_dtbo_candidate_members=['dtbo.img.lz4']
m25_stock_dtbo_rollback_sha256=6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
m25_stock_dtbo_rollback_members=['dtbo.img.lz4']
```

Android preflight:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
android_stability_result=ok samples=4
```

Current partition hashes:

```text
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
dtbo        97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
```

Additional validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  tests/test_s22plus_m25_hs_only_usb2_acm_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m25_hs_only_usb2_acm_live_gate

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  --offline-check
```

Results:

- `py_compile`: pass
- unit tests: `Ran 5 tests ... OK`
- `--offline-check`: pass, no device action
- default dry-run: pass, no flash/reboot/write

## Next Step

The next actual experiment is the attended live gate:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  --live --ack S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE
```

If the operator manually enters Download mode after a loop or no-transport
result, run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  --rollback-from-download --ack S22PLUS-M25-HS-ONLY-ROLLBACK-FROM-DOWNLOAD
```
