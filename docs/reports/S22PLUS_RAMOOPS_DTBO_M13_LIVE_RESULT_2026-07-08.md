# S22+ Ramoops DTBO + M13 Live Result (2026-07-08)

## Scope

Attended S22+ DTBO-enabled M13 positive-control capture run after active policy
promotion. This report is redacted and metadata-only; raw logs and pstore
captures remain under `workspace/private/runs/`.

## Pre-Live Gates

- Host-only missing-Download cleanup hardening committed first.
- `AGENTS.md` policy was promoted only after operator live approval.
- Active-policy readiness passed with `agents.complete=true`.
- Pre-live dry-run passed before any write: Android/root stability, current boot
  hash, current stock DTBO hash, and live `ramoops_region/status=disabled` were
  verified.

## Live Sequence

The first live command used the active ack-gated helper:

```text
s22plus_ramoops_dtbo_m13_capture_live_gate.py --live --ack <active-token>
```

Observed flow:

```text
dtbo_candidate_odin_rc=0
patched_dtbo_hash_rc=0
patched_ramoops_status=okay
m13_candidate_odin_rc=0
m13_acm_seen=0
m13_result=no_rollback_transport_manual_download_required
live_rc=4
```

Interpretation: the DTBO enable path worked and the M13 boot candidate Odin
flash returned success, but M13 did not expose ACM, ADB, or Odin rollback
transport inside the bounded observation window.

## Rollback And Cleanup

The attended rollback helper was then run:

```text
s22plus_ramoops_dtbo_m13_capture_live_gate.py --rollback-boot-from-download --ack <rollback-token>
```

Result:

```text
magisk_boot_rollback_odin_rc=0
post_m13_boot_rollback_pstore_files=[]
post_m13_boot_rollback_last_kmsg_bytes=2097136
post_m13_boot_rollback_pstore_marker_found=0
post_m13_boot_rollback_last_kmsg_marker_found=0
m13_positive_control_pstore_marker_found=0
stock_dtbo_rollback_odin_rc=0
stock_restore_dtbo_hash_rc=0
stock_restore_ramoops_status=disabled
rollback_helper_rc=10
```

`rc=10` is the helper's "rollback/restore completed but expected M13 marker was
not found" result, not a rollback failure.

## Final State

Final read-only verification:

```text
boot_hash=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo_hash=97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
final_dryrun=pass
```

The final helper dry-run reverified Android/root stability, Magisk boot
baseline, stock DTBO hash, and live `ramoops_region/status=disabled`.

## Result

Live result: **NO-HIT for M13 positive-control pstore marker**.

Clean-state result: **PASS**. The device is back on the Magisk boot baseline
with stock DTBO and Android/root available.

## Next Direction

The DTBO half is proven. The M13 half still provides no host-visible signal and
no retained marker. The next candidate should avoid relying on a passive park
plus pstore retention alone; it needs an earlier deterministic retained signal
or a bounded intentional reset path whose marker is known to reach the retained
log surface.
