# S22+ FYG8 P3.19 D0 fresh-baseline producer H0

Date: 2026-08-24 KST

Status: `PASS_GO_P319_D0_FRESH_BASELINE_H0_CAPABILITY_V1`

This unit implements the connected-read-only half of the P3.19 fresh-baseline
producer, but only as host-side capability code. It created no approval, arm,
run, stop, D0 result, normalized baseline or device contact. Independent
review qualifies the exact capability closure; it is not a current operator
approval and does not itself invoke the live entry point.

## Execution closure

The D0 producer is 71,975 bytes with SHA-256
`c1a7f82ff9a7e9ca555cf38a9f8addaf7d287f7a5560057b9be49899c631062f`.
The reviewed reducer is 64,375 bytes with SHA-256
`2729426d63c512b6fcecd1bb4b6c6b8f399882b317e02b758080ae9add0cb17c`.
The canonical 14,240-byte D0 execution binding is SHA-256
`34203813fe3c4bf979a7dd2bc575ade80f935eec1ca7fdedbae8096e8822c848`
and records exact verdict `PASS_GO_P319_D0_FRESH_BASELINE_H0_CAPABILITY_V1`.

The binding pins the exact target/profile, current 437-source/73-row/EUD38/
latch-only candidate identity, D0 runtime, raw-capture helper, all 39 P3.19
adapter sources, exact ADB bytes and snapshot path, fixed run/arm/stop names,
and the D1 result dependency. The D1 source is unchanged at
48,354 bytes / `e0fa9d40e58e2ab372fa3f89005b51a33e17aeb47c21c2b42cdb0bbe35edad55`.
Its repinned 4,128-byte binding is now
`0a91beec8cad13622bb29c2f7865a08d37fd4531da984b9423024f6f7b9dd63b`.
It retains the topic-40 `pass-go` tuple, and topic-41 independent review closes
the joint reducer/D0 changed closure. The earlier `cb36cce8`, `1ea4f930` and
`d92e7e46` bindings were never approved, armed or run and remain explicit
unconsumed predecessors.

The exact capability-bound future authority form is
`DEVICE-ACTION-D0-P319-FRESH-BASELINE-V1-APPROVE:34203813fe3c4bf979a7dd2bc575ade80f935eec1ca7fdedbae8096e8822c848`.
Recording that form is not a current operator approval and does not authorize
a run. The producer still enforces exact `--live --approval TOKEN` syntax and
all fixed pre-contact input checks.

## Raw-first and result boundary

After a durable fixed intent, the design admits exactly one S22+ target and
permits zero commands to other targets. It cross-binds the reviewed D1 result's
serial, topology and returned boot ID to both D0 health edges; Download
endpoints must remain zero. The only observer acquisition is one bounded
`/proc/last_kmsg` read. The common raw writer must publish exactly 2,097,136
stdout bytes and empty stderr before the pinned P3.19 classifier receives the
reopened handle. Only `ZERO_AMBIGUOUS`, integrity-clean, candidate-marker-
family-absent evidence can publish success.

Every generic target/health command is retained through a closed
`raw-adb/` inventory of **9 handles / 27 children**. Each handle, stdout and
stderr file is stable-reopened, mode/link/type checked, and included in a
canonical aggregate digest. Extra, missing, indirect or mutated children fail
closed. A post-intent failure publishes a typed consumed stop where possible;
pre-intent rejection produces no stop and no effect. The reducer reopens the
exact D0 binding, arm, result, raw observer, ADB snapshot and complete raw-ADB
inventory instead of trusting embedded booleans.

## Permanent raw-first registration

The D0 source is a **migrated active raw-first source**, not a pre-boundary
exception. Its `_execute` seam is bound to acquire, require-success, stdout,
stderr and classify ordering, while `_raw_adb_inventory` is bound to reopened
handles and complete child accounting. Direct subprocess output parsing and
removed or reordered seams remain rejected.

The current raw auditor is 64,544 bytes at SHA-256
`ab6c04b5acbe01dce3f3aadd25abf387849b7447b4d615151f8324d65e387ced`
with normalized self-hash
`bfb094af111f5251a0e2d96e95eda93be0ae919efcacce887b5ffbae305c0751`.
It scans 1,739 revalidation Python files and 412 subprocess-import modules.
Pre-boundary S22 membership stays 128 at
`fcb3bb805ccbadb7277ecf4922ebd0d9c603f44204a9a0889162fceafb68bf95`,
and target-external membership stays 52. Active raw-first membership is 16.

The no-clobber successor
`raw-first-observer-audit-20260824-03-p319-d0-fresh-baseline.json` is 11,792
bytes at SHA-256
`9c5d892c032c972fef1106dd9c564664ae69049409d31b1008d11f42fe2ef1ea`,
mode `0400`, link count one. The `-02` `ff1cab64`, `-01` `b56ef046`,
`20260823-04` `ac3876c0` and all earlier receipts remain byte-preserved.

The repinned prerequisite auditor is 45,264 bytes at SHA-256
`a861ee7b31cc008b6a3af99e1aef178c47e7d753032219d63380f6e9b68f6c8b`.
Its no-clobber `process-v2-prerequisite-audit-20260824-03.json` is 12,534
bytes at SHA-256
`3e62512e4533d3e7ab9a92302286a0f892e84a7f2602b213634c18289556e735`,
mode `0400`, link count one. The `-02` 12,530-byte `26c8eb9d` receipt and all
predecessors remain preserved.

## Boundary

Independent review now makes a deterministically reconstructed hypothetical
normalized result emit `producer_execution_closure_reviewed=true` and
`producer_execution_closure_authoritative=true`; `validate_published_result`
returns authoritative only after reopening the exact reviewed D1/D0 bindings,
results, journals and raw handles and reproducing canonical equality. No such
current normalized result exists, so machine integration remains
`BLOCKED_P319_PROCESS_V2_INTEGRATION_H0` on `FRESH_BASELINE_MISSING`. Its
`ready`, live, D0/D1/F1, replay, candidate-success and causal-result fields
remain false. No ready/run/public candidate manifest, current approval, arm,
run, result or device contact exists.

Final-tree validation is: D0/D1/reducer/integration `82/82`; permanent
raw-first `23/23` in 595.870 seconds; prerequisite `9/9`; raw/integration docs
plus taxonomy `66/66`; and common Process-v2 `142/142`. The broad P3.19
selection is exactly 656 tests: 655 passed, zero failed and one error because
`/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko` is unavailable.
That unavailable external input is not reported as a pass.
