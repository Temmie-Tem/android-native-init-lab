# S22+ M25 Hash-Gate Hardening (2026-07-08)

## Scope

Host-side/live-gate hardening only. No live flash, reboot, rollback, partition
write, or sysfs write was performed.

## Change

`s22plus_m25_hs_only_usb2_acm_live_gate.py` now reads Android partition hashes
with direct block-device hashing:

```text
su -c 'sha256sum /dev/block/by-name/<part> 2>/dev/null || toybox sha256sum /dev/block/by-name/<part>'
```

The previous `dd if=... | sha256sum` shape could hide a failing `dd` behind a
successful `sha256sum` over an empty stream. A mismatch would still fail closed,
but the command rc was weaker evidence. Direct hashing keeps read failures tied
to the command rc.

The helper also rejects unsafe partition names before building the shell command,
and the M25 live runbook now uses one direct-hash command per partition for
post-rollback verification.

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_s22plus_m25_hs_only_usb2_acm_live_gate
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py --offline-check
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py
git diff --check
```

Results:

```text
unit tests: Ran 9 tests ... OK
offline-check: ok
dry-run: ok
dry-run log: workspace/private/runs/s22plus_m25_hs_only_usb2_acm_live_gate_20260708T121540Z/s22plus_m25_hs_only_usb2_acm_live_gate.txt
```

Dry-run baseline evidence:

```text
android_stability_result=ok samples=4
current_boot_hash_rc=0
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e  /dev/block/by-name/boot
current_vendor_boot_hash_rc=0
096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7  /dev/block/by-name/vendor_boot
current_dtbo_hash_rc=0
97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c  /dev/block/by-name/dtbo
```

## Status

M25 remains live-ready but not executed in this unit. Live still requires the
operator-attended command with exact ack:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py --live --ack S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE
```
