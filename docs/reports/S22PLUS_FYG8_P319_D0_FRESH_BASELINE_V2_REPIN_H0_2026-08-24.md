# S22+ FYG8 P3.19 D0 fresh-baseline V2 consumer/reducer repin

Date: 2026-08-24 KST

Status: `P319_D0_FRESH_BASELINE_V2_REPIN_IMPLEMENTED_REVIEW_PENDING`

## Result

The reviewed D1 V2 capability is now consumed by a separately versioned H0 D0
producer and reducer design. The new producer is 72,288 bytes at SHA-256
`e1190b66a31ee674d9f0bf64726fbf8a5edb55d81e7910b07b6f4b0f46009d0d`;
the new reducer is 54,126 bytes at SHA-256
`ea72adab0690b2c2e52e15829a7a98632ef59b7e36d77f8a29a9db6e532f6ef3`.
Their canonical review-pending execution binding is 14,251 bytes at SHA-256
`bda6b82d9689b8968edc9cd2b7b0190c75bef9629b3a3f24443e7096ebb7cd55`.

The binding fixes `d0-p319-fresh-baseline-2`, the V2 schemas and authority
prefix, exact target/profile/current 437-source/73-module/EUD38/latch-only
candidate identity, reviewed D1 V2 source `66357B/9443c81c`, reviewed D1 V2
binding `5351B/65e2953e`, common raw-first runtime, complete adapter graph and
exact host ADB. The historical D1 V2 review-pending binding
`5300B/917daa02` is recorded only as an unconsumed predecessor.

The future authority format is
`DEVICE-ACTION-D0-P319-FRESH-BASELINE-V2-APPROVE:` followed by the complete
binding digest. This is a format, not a current approval. The binding remains
review-pending.

## Exact D1 V2 consumption

The reducer stable-reads the exact D1 V2 source and pass-go binding before
compiling only those pinned source bytes. It then runs the D1 V2 source's own
`_validated_static_inputs`, `_validated_execution_inputs`, `_result_complete`,
selection and raw-inventory validators and performs post-load stable reopens.
Acceptance requires the fixed `p319-fresh-baseline-2` result path and namespace,
exact execution-manifest and approval digests, direct arm/start receipts, exact
ADB snapshot, complete raw-handle inventory, distinct before/after boot IDs,
typed selection, one reboot and every zero-effect/no-replay flag. The reducer
reopens the fixed raw namespace and requires canonical equality with the
result's `raw_evidence`; a summary boolean is not authority.

A V1 D1 result, the consumed V1 stop, or a V2 stop is not an alternative input.
Schema, fixed path, journal, namespace and exact validator checks reject each.
Extra entries, hardlinks, symlinks, receipt replacement and identity drift fail
closed. The D0 producer never writes or traverses the D1 V2 namespace.

## Version separation and inherited contracts

The previous D0 producer, reducer and binding remain exact evidence:

- V1 D0 producer: `71975B/c1a7f82f`;
- V1 reducer: `64375B/2729426d`;
- V1 D0 binding: `14240B/34203813`.

The V2 producer retains the reviewed V1 raw-first acquisition, nine-handle /
27-child inventory, typed stop, no-clobber, cut-state and namespace semantics,
but all producer, D1/D0 journal, result, binding, version and ordinal literals
are V2. The remaining `v1` names are intentional common inputs: current
candidate intent/qualification schemas, `device_action_raw_capture_v1`, the
existing raw-ADB inventory ABI and the stock-witness Carrier contract. Tests
freeze this distinction.

## Current fail-closed state

There is no `d1-fresh-baseline-2` arm, start, result, raw namespace or ADB
snapshot. Consequently there is no V2 D0 approval, arm, run, stop or result,
and no normalized `fresh-baseline-v2/result.json`. The H0 self-test records both
the D1 V2 result and fixed D0 result as absent. Integration consumes only the
V2 reducer/path and still returns exactly `FRESH_BASELINE_MISSING`, with ready
and live authority false. No public candidate, ready or run manifest is made.

## Permanent raw-first and prerequisite evidence

The V2 D0 producer is the 18th active raw-first source; V1 remains the 16th
active predecessor and D1 V2 remains the 17th. The raw auditor is 68,231 bytes
at SHA-256 `0cfd391b2ca26ddd8f51cac9fe2b7fcb14daaeba5985d4541e8b08354e9c0487`
with normalized self-hash
`0aa0a9b10ce55cd0f33b2a23a13e8b06e5ed7ee5d0ec25e298df5d53bbc9f24a`.
Its census is `1742/412`; S22 pre-boundary `128/fcb3bb80` and target-external
52 remain unchanged. The no-clobber `-06` receipt is 12,916 bytes at SHA-256
`66658f6739b8e0116209a13de3fbb2255b040fa68b0ee7bb34c7cb51876207ec`,
mode `0400`, link count one; `-05` and every predecessor remain byte-preserved.

The prerequisite auditor is 45,258 bytes at SHA-256
`8ba7a3312f2a978941d578a2dd06d489a6242d232e0aa7cd33d7b3c26b9b3223`.
Its no-clobber `process-v2-prerequisite-audit-20260824-06.json` receipt is
12,528 bytes at SHA-256
`7a5a824893dc40d2f284d6e719bad0d7e56ff92c358ddc921711fa46ef6955d0`,
mode `0400`, link count one. The V2 integration source is `51990B/e35e2e81`;
its deterministic blocked receipt is `61379B/49745fc2`, mode `0400`, link count
one. All three current artifacts are H0 and authority-free.

## Validation and boundary

The V2 producer hostile suite passes `29/29`; the V2 reducer/D1 authority suite
passes `11/11`, and the integration qualification adds `14/14`, for focused
`54/54`. Permanent raw-first passes `24/24`; prerequisite, raw/integration docs,
taxonomy and consumed-stop evidence pass `79/79`; common Process-v2 passes
`142/142`. Broad P3.19 is exactly 728 total: 727 passed, zero failed and one
known unavailable `/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko`
input error, which is not reported as a pass.

Independent changed-closure review is required. Topic 43 is the only new
obligation. The V1 action remains consumed and non-replayable, the reviewed D1
V2 capability is not a current approval, and the absence of its result keeps
D0 V2 unavailable. This unit creates no approval, arm, run, result, ready/run
manifest, D0, D1, F1, recovery, replay, causal result, candidate success,
device, ADB, USB, Odin or live authority and touches no A90 or S20+ state.

## Append-only independent-review correction — 2026-08-24 15:40:13Z

Independent review blocked the implementation tuple above. The reviewed D1
V2 `_result_complete` predicate compared the result's direct arm/start
receipts with the actual files, but did not apply `_arm_complete` or
`_start_complete` to those files. A canonical `{"foreign":"arm"}` or
`{"foreign":"start"}` replacement, accompanied by the matching updated
result receipt, therefore passed that predicate and the predecessor reducer.

The D1 V2 source and binding are unchanged. The repaired reducer now invokes
the exact compiled D1 V2 `_journal_state` on the fixed arm and start paths,
using `_arm_complete` and `_start_complete`, after `_result_complete` has read
their direct receipts. Both states must be present, node-valid and
bytes-complete, and each stable-reopened receipt must exactly equal the result.
The hostile suite performs the actual foreign canonical replacements and
updates the result receipts; both are rejected.

The predecessor reducer `54126B/ea72adab` and binding `14251B/bda6b82d`
remain unreviewed historical identities. The repaired reducer is
`54939B/d6d4c766047b00475205a7ff945f254b5a2857409f13311352cfacf010028780`;
the canonical review-pending binding is
`14251B/4be15cba9afa7524fe90cf7f97d429e3a6e710d735fa557e7a287fe97386c667`.
The D0 V2 producer remains byte-identical at `72288B/e1190b66`; therefore its
active raw-first source identity and the `-06` receipt remain byte-identical.
The prerequisite `-06` and deterministic blocked integration receipt also
remain byte-identical after independent regeneration. Topic 43 remains the
single open review obligation; the repair creates no PASS_GO or live authority.
The repaired focused split is `29/29 + 12/12 + 14/14 = 55/55`; the added
hostile regression makes the current broad selector 729 tests. The preceding
728-test paragraph is the implementation predecessor result and is not
retroactive validation of this repair.
