# S22+ FYG8 P3.19 D1 fresh-baseline consumed stop

Date: 2026-08-24 KST

Status: `STOP_P319_D1_FRESH_BASELINE_CONSUMED_NO_REPLAY`

At `2026-08-24T11:17:59Z` (`20:17:59 KST`), the operator supplied the exact
approval bound to the reviewed 4,128-byte execution binding
`0a91beec8cad13622bb29c2f7865a08d37fd4531da984b9423024f6f7b9dd63b`.
The D1 attempt consumed that approval and its fixed run ordinal. This report is
post-effect accounting; it does not authorize a retry or a replacement run.

## Durable evidence

The fixed arm
`workspace/private/runs/device-action-d1-p319-fresh-baseline/p319-fresh-baseline-1.arm.json`
is 708 bytes at SHA-256
`1d64712e342968ae6a3574104248ea93f485cd8247db6c646bc47f57275d8aa7`,
mode `0400`, link count one. It is canonical and complete, records attempt one
as consumed, records no pre-arm device contact, and binds the exact current D1
execution manifest.

The fixed ADB executable snapshot is 716,968 bytes at SHA-256
`05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226`,
mode `0500`, link count one. Its presence does not prove a successful target
read or final health.

The fixed run directory is direct, mode `0700`, and contains exactly one child:
`stop.json`. That stop is 943 bytes at SHA-256
`ad0cae49fd88cadbcb6f7be54afca6448b3fa4cd2cb2b02a1c0bfab2ab6bc326`,
mode `0400`, link count one. The reviewed D1 `validate_stop_file()` accepts the
exact absolute path and reopens its namespace.

The stop records:

- stage `after-arm-before-start`;
- error type `D0Error`;
- complete arm, absent start and absent result;
- `reboot_dispatch_possible=false` and `device_contact_unknown=true`;
- candidate transfer, partition payload, Odin, Download transition, F1,
  replay authorization and reusable result all false.

No D0 run directory, D0 arm, D0 stop or normalized fresh-baseline result exists.
There was no retry.

## Interpretation boundary

Only the exception type was retained. It does not distinguish target inventory,
topology, health or client-read failure, so this report does not infer a cause.
The durable evidence proves that no reboot command was dispatched, but it does
not contain a formal final-health observation. The ledger therefore records
`HEALTH_PENDING / NO_PROOF_OBSERVER`, not healthy completion.

The reviewed D1 and D0 producer capabilities remain valid as capabilities, but
this D1 approval and run ordinal are consumed permanently. Candidate replay is
forbidden. D0 fresh-baseline acquisition cannot begin because it requires a
valid D1 result, which is absent. Integration remains
`BLOCKED_P319_PROCESS_V2_INTEGRATION_H0` on `FRESH_BASELINE_MISSING`. There is
no current approval, ready/run/public candidate manifest, D0/D1/F1/recovery,
candidate-success, causal-result or live authority.

## Validation

The exact consumed-stop evidence tests pass `4/4`; taxonomy plus integration
documentation tests pass `47/47`. Test discovery contains 660 P3.19 tests after
adding the four evidence tests. The attempted broad execution is invalid and
must not be cited as a pass: `/tmp` reached `ENOSPC`, so unittest reported only
581 run, 6 failures and 113 errors, dominated by failed temporary-file writes;
the known unavailable `/mnt/.../spu_verify.ko` error was also present. No
scratch directory was deleted and the broad suite was not retried.
