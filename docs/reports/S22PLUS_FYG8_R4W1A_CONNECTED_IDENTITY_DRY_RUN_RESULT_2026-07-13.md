# S22+ FYG8 R4W1-A Connected Identity Dry-Run Result

Date: 2026-07-13 KST
Scope: attended connected read-only identity and observer preflight
Device write: none
Reboot, Download transition, Odin transfer, or flash: none

## Verdict

`PASS_R4W1A_CONNECTED_IDENTITY_DRY_RUN_READ_ONLY`

The exact R4W1-A helper passed its connected read-only gate against one normal
FYG8 Android target. The run created the SHA-bound connected promotion record
required by a future oracle-policy review. It did not run `bugreportz`, consume
the oracle rehearsal, activate candidate policy, reboot the device, or write
the device.

## Executed Unit

- helper SHA256:
  `6dcf003c2c0ef186e4001af44da8cc526014d1704c8b25d7ba04788afd9ca577`;
- acknowledgement:
  `S22PLUS-FYG8-R4W1A-CONNECTED-IDENTITY-DRY-RUN`;
- private run:
  `workspace/private/runs/s22plus_fyg8_r4w1a_connected_dry_run_20260713T083218Z`;
- result SHA256:
  `1a338070008e06b4f8b0e62302c5099be82270c5893352b126dab4ae3c193926`;
- connected promotion-record SHA256:
  `63dc2b8d27ebd04ef66ce3cb8e3151a12e491fbf46e3242605a40694205db041`.

Before device contact, the helper reran the independent artifact checker and
reproduced exact result SHA256
`fc528ba9c8acce18a636d398a13add42a7882e7bfd505e82d63ff861e0963a0b`
with verdict `PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT`.

## Connected Evidence

The preflight proved:

- exact `SM-S906N` / `g0q` / `S906NKSS7FYG8` identity;
- Android boot complete, boot animation stopped, and Magisk `uid=0(root)`;
- known Magisk boot SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- stock DTBO SHA256
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- stock recovery SHA256
  `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`;
- no Odin endpoint;
- live `sec_log_buf` and exact bind
  `/sys/bus/platform/drivers/samsung,kernel_log_buf/8.samsung,kernel_log_buf`;
- EOF-complete 2,097,136-byte reads of both `/proc/ap_klog` and
  `/proc/last_kmsg`;
- zero exact, family, suspicious, or boundary-partial R4W1 marker evidence in
  both snapshots.

The timeline uses only the required
`events:[{name,timestamp_utc}]` schema and contains all eight mandatory phase
names. Candidate and rollback flash phases are explicitly classified as
read-only no-flash semantics.

## Independent Close

Host-side rehashing reproduced the result SHA named by the promotion record
and promotion-record SHA reported by the helper. The oracle consumed record,
oracle PASS record, and candidate consumed record all remained absent. The Git
worktree was clean immediately after the live run because private evidence is
not committed.

## Boundary And Next Gate

This PASS proves the exact baseline and observer reads needed before an oracle
rehearsal. It does not prove the actual FYG8 `bugreportz` streamed ZIP shape,
remote cleanup behavior, candidate boot, retained PID1 marker, or rollback.

The next unit is host-only independent review and explicit activation of only
the one-capture, zero-flash oracle dry-run clause using the connected
promotion-record SHA above. A fresh attended oracle acknowledgement is still
required after that review. Candidate policy and candidate flash remain
blocked until the oracle rehearsal passes and receives a separate review.
