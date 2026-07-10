# V3437 S22+ Ramoops Positive-Control Live Result

## Verdict

`FAIL_PREPANIC_GATE_ROLLBACK`.

The candidate DTBO booted Android and passed its live-DT and module-parameter
checks, but the required ramoops backend-registration proof was absent. The
helper stopped before marker arm or panic and restored the stock DTBO. This is
not a ramoops retention result because no panic was attempted.

## Run Identity

```text
run_id=e64f143c09d9206918638f46b7492b10
run_dir=workspace/private/runs/s22plus_v3437_ramoops_20260710T230320Z
candidate_ap_sha256=622ac0259eb61a7c9ef71eff44d4ea8bb3edbc6a90c3f2b237be7fdf88cb0264
candidate_dtbo_sha256=3c4d38a9d4833bab648cd36c3c0c78a2bfed35ca80dc4532b5e877cbaa8fa281
rollback_ap_sha256=6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
stock_dtbo_sha256=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
magisk_boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

## Sequence

1. Active-policy offline check passed with no device action.
2. Read-only dry-run passed the stock Android, root, boot, and DTBO baseline.
3. Candidate DTBO-only Odin transfer completed with rc=0.
4. Android returned and passed exact target/root/boot checks.
5. Candidate raw DTBO readback matched the pin.
6. Live DT reported `status=okay` and the exact 2 MiB ramoops layout.
7. `/sys/module/ramoops/parameters` matched the expected 1 MiB pmsg, 512 KiB
   console, and two 256 KiB dmesg records.
8. Pstore was mounted and `/dev/pmsg0` existed, but the required backend
   registration marker was absent.
9. The helper stopped before marker arm and panic, entered the pre-panic
   rollback path, and flashed the stock DTBO-only AP with rc=0.
10. Stock Android returned and passed four stability samples, exact Magisk boot
    and stock DTBO hashes, and `ramoops_region/status=disabled`.

## Durable State

```text
state=CLASSIFIED
classification=FAIL_PREPANIC_GATE_ROLLBACK
panic_attempted=false
evidence_abandoned_for_recovery=true
candidate_flash_done=2026-07-10T23:03:44Z
rollback_flash_done=2026-07-10T23:04:29Z
rollback_boot_ready=2026-07-10T23:05:11Z
live_session_end=2026-07-10T23:05:11Z
```

The helper process exited with the original backend-gate error after completing
and recording the successful rollback. The final session and timeline files are
complete.

## Post-Run Read-Only Evidence

The first stock boot after rollback exposed a 2,097,136-byte
`/proc/last_kmsg`, SHA256
`d6a7bc92b12a472f78ffb2567dae1cdea99dc703ffa0ca26849b154cb5a8c8ae`.
A bounded search found no ramoops/pstore registration or ramoops probe-failure
line. This does not prove that no probe happened; it means the retained Samsung
log did not supply the missing backend proof.

Final live readback:

```text
Android ADB=rooted and boot_completed=1
bootanim=stopped
boot_reason=reboot,download
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_sha256=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
ramoops_status=disabled
```

## Interpretation

The run proves that the DTBO overlay and size properties reach the live tree,
but it does not prove that a ramoops platform backend binds to the region.
Pstore mount and `/dev/pmsg0` are insufficient because they also exist without
the candidate backend. Repeating the same DTBO and panic sequence is not
justified. The next unit is host-only analysis of the exact platform-device
creation and ramoops bind path, including whether this Samsung kernel treats
the mainline-style node as vestigial.

Both V3437 one-shot policies are retired. No repeat candidate flash or panic is
authorized.

## Post-Run Validation

```text
V3437 focused tests                    16/16 PASS
V3426-V3437 regression tests         165/165 PASS (57.760 s)
offline policy status                dtbo_active=false panic_active=false
git diff --check                     PASS
```
