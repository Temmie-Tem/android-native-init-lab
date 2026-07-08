# S22+ M29 First-Rollback Capture Live Gate (2026-07-08)

Superseded on 2026-07-09 KST by
`S22PLUS_M29_FIRST_ROLLBACK_CAPTURE_LIVE_RESULT_2026-07-09.md`. The M29 live
gate was consumed, produced no clean S24 self-download proof, required operator
manual Download recovery, and is no longer authorized. Do not use this
pre-live report as an active runbook.

## Verdict

POLICY ACTIVE / PRE-LIVE DRY-RUN PASS / LIVE NOT EXECUTED.

Codex promoted a fresh, SHA-pinned `AGENTS.md` exception for exactly one M29
first-rollback capture run. The helper dry-run passed against the attached S22+
Android/Magisk baseline. No live flash, reboot, rollback, partition write, or
sysfs write was performed.

## Helper

```text
workspace/public/src/scripts/revalidation/s22plus_m29_first_rollback_capture_live_gate.py
```

Helper SHA256:

```text
d8da7792f9ccc60a16358984636b29a3df27fac6b264f039354ea54770a18bb3
```

`AGENTS.md` SHA256 after promotion:

```text
4d92c4a13e321fea2cf1c7e74069067927a7055875233d6b4ca6b551cf3bc698
```

## Authorized Live Shape

M29 is a collection-order gate, not a new candidate build. The authorized run is
limited to the existing M28 dependency-complete `S24` candidate:

```text
S24 AP.tar.md5 SHA256  c684f6a21bcc9aa50b066b447f4356958fe6d7bfed93edf0ac1b7dcaae8ce75f
S24 boot.img SHA256    a1459931001bfd6e17593dd329fc682f00ab61f4841b6543791f5349dd012cd0
S24 /init SHA256       5c04a2023b2b56ef98746da6f7168121b62d7859cee81c756b80d1a382c1964e
S24 modules SHA256     8c605e2c69aad74f80191bdbc1843b002539d22d49bcffa86bb85bbcb343e5e4
```

`F43` remains unauthorized. The helper rejects non-`S24` selection.

The live path must:

1. Verify baseline Android/Magisk and stock DTBO.
2. Apply the M25 high-speed DTBO cap if needed.
3. Capture a pre-candidate retained-log baseline.
4. Flash S24.
5. Roll back boot to Magisk when Download mode appears.
6. At the first post-candidate Android boot, before stock-DTBO rollback, capture
   `/proc/last_kmsg`, pstore, `/proc/reset_summary`, `/proc/reset_klog`,
   `/proc/reset_history`, `/proc/reset_tzlog`, and reset-reason summary.
7. Compare pre-candidate and first-rollback `last_kmsg` SHA256.
8. Restore stock DTBO only after the first-capture step.

Any operator manual Download is contamination: it may be used for recovery and
first-rollback capture, not as clean self-download proof.

## Dry-Run Command

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m29_first_rollback_capture_live_gate.py \
  --serial <REDACTED_S22PLUS_SERIAL>
```

Run log:

```text
workspace/private/runs/s22plus_m29_first_rollback_capture_live_gate_20260708T145747Z/s22plus_m29_first_rollback_capture_live_gate.txt
```

Result:

```text
dry-run ok: M29 S24 candidate, M25 DTBO cap, rollback APs, AGENTS exception,
Android stability, boot/vendor_boot/stock-DTBO hashes verified
```

Key dry-run evidence:

```text
agents_exception_missing=[]
android_stability_result=ok samples=4
current_boot_hash_rc=0
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
current_vendor_boot_hash_rc=0
096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
current_dtbo_hash_rc=0
97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
```

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m29_first_rollback_capture_live_gate \
  tests.test_s22plus_m28_dep_complete_live_gate
```

Result:

```text
Ran 16 tests in 0.030s
OK
```

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m29_first_rollback_capture_live_gate.py \
  tests/test_s22plus_m29_first_rollback_capture_live_gate.py
```

Result: pass.

## Next

None under this gate. M29 is consumed/retired; S24 repeat and F43 remain
unauthorized without a fresh, narrower exception.
