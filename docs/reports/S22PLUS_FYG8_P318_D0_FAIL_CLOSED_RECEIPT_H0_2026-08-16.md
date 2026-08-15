# S22+ FYG8 P3.18 D0 Fail-Closed Receipt H0

Date: 2026-08-16 KST

## Status

`PASS_GO_P318_D0_FAIL_CLOSED_RECEIPT_H0_CAPABILITY_V1`

Independent review approves only this exact host-only repair of the reusable
Process-v2 D0 adapter. It creates no D0, D1, F1, recovery, replay, or live
authority. The P3.18 candidate bytes are unchanged, but the changed execution
closure still requires downstream requalification before another connected
prerequisite run.

## Trigger

The exact S22+ P3.18 prerequisite D0 at `2026-08-16T02:41:26KST` selected
`SM-S906N/g0q` from a two-device ADB inventory and completed initial identity,
rooted-health, supporting-partition, and no-Download checks. It preserved a
2,097,136-byte `/proc/last_kmsg` read with empty stderr and SHA-256
`758ad7360f43baa14ca2e5f4ad3d72b00c31ec829caeb365f1de91a6b67aefd8`.

The raw input contains three integrity-clean, foreign-count-zero residual
P3.17 Carrier-v2 records: two identical generation-107 stage-147 detail-0x6710
`pre-nonusb-post-stable-usb` terminals and one generation-95 stage-144 progress
record. Rejecting that non-clean baseline was correct. The defect was that the
selected decoder's `DesignError` escaped the D0 `EvidenceError` boundary, so the
CLI returned a traceback and preserved no `result.json`.

The append-only campaign ledger now records the D0 as
`RETAINED_BASELINE_HOST_STOP / HEALTHY / NO_PROOF_OBSERVER / 0/0`. That row
does not promote the offline sub-decode into a successful D0 qualification.

## Repair

`device_action_d0_v2.py` now normalizes selected baseline-decoder contract
failures at the D0 boundary and distinguishes two closed stop reasons:

- `baseline-decoder-rejected`; and
- `retained-evidence-present`.

Once the bounded raw capture is complete, either reason produces schema
`device_action_d0_stop_result_v1` at the ordinary private `result.json` name
before the adapter returns failure. The receipt binds:

- the exact profile, manifest, bundle, target evidence, and host tool;
- initial rooted health and initial no-Download USB evidence;
- the raw observer path, byte count, SHA-256, EOF result, empty stderr, and
  elapsed bound;
- the exact stop stage and reason; and
- false device-write, reboot, Download-transition, Odin, partition-transfer,
  F1, and live-authority flags.

It explicitly records `final_target_continuity_observed=false`,
`final_health_observed=false`, `final_observed=false`, and
`result_reusable=false`. The ordinary success validator rejects this schema,
and the stop validator reopens the raw bytes and stderr, reruns the baseline
boundary, and requires the same stop reason. Failures before a complete bounded
capture do not manufacture a raw-evidence receipt.

## Captured-Input Replay

A host-only replay fed the preserved 2,097,136-byte input through the repaired
adapter with synthetic target transport. It produced and reopened exactly:

- schema `device_action_d0_stop_result_v1`;
- verdict `STOP_DEVICE_ACTION_D0_V2_BASELINE_REJECTED`;
- reason `baseline-decoder-rejected`;
- observer SHA-256 `758ad7360f43baa14ca2e5f4ad3d72b00c31ec829caeb365f1de91a6b67aefd8`;
- `final_health_observed=false`; and
- `result_reusable=false`.

The tracked focused fixture uses the exact current P3.18 acceptance contract and
a valid Carrier-v2 record preimage. It proves that the prior unhandled decoder
exception now yields a mode-0400 durable stop receipt, only one target-selection
pass, no final target read, and no authority. Reason, final-health, bool/integer,
path, USB, and raw-byte mutations reject.

## Validation

- D0 adapter tests pass 22/22, including hostile-umask exact-mode publication.
- D0/report/taxonomy/P3.18/common-doc focused tests pass 96/96.
- The four common Process-v2 modules pass 120/120.
- All current P3.18 modules pass 141/141.
- Independent review binds adapter SHA-256 `fc4849381bfc`, D0-test SHA-256
  `e660877a0ae2`, and reproduced the actual captured-input stop receipt.
- The taxonomy receipt independently regenerates byte-identical at 23,314
  bytes, SHA-256 `6541ed535aec`, mode 0400, link count one despite the two valid
  post-scope rows.
- Python compilation and scoped whitespace checks pass.

## Inter-Target Handoff Boundary

The failed D0 process ended synchronously before the later independently bound
S20+ continuation. The S20+ terminal records zero S22+ commands, so no S22+
command or live session crossed that target boundary. Initial S22+ health had
passed before the retained read. No durable post-stop S22+ continuity or final
health receipt exists, however, and this repair does not infer one
retroactively.

## Offline Closure Impact

The common Process-v2 contract is one of the 42 P3.18 intent source receipts.
A fresh host-only intent derivation therefore differs from the approved V3
intent only at `process_v2_contract`: the old 33,005-byte `2a6e48c9` receipt is
now 33,498-byte `72f1eb61`. The materialized sources and candidate patch remain
byte-identical; the patch SHA-256 remains `d839850e6e95`.

The canonical ready-manifest verify-only path now fails closed with
`P3.18 overlay intent verification failed`. No canonical intent, candidate,
qualification, Process-v2 evidence, ready manifest, or private ready file was
overwritten. That is the correct state until this changed common closure is
reviewed and its downstream host-only receipts are regenerated.

## Independent Review and Remaining Gate

Independent review is complete for the exact H0 stop-receipt closure. The
Process-v2 execution closure and ready evidence must still be regenerated
against the repaired adapter. Only then may one fresh exact D1
baseline-rotation approval be requested, followed by a new exact S22+ D0. No
reboot or connected retry is authorized by this report.
