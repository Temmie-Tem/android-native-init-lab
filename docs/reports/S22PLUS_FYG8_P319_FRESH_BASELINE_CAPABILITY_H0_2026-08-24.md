# S22+ FYG8 P3.19 fresh-baseline capability H0

Status: `PASS_GO_P319_FRESH_BASELINE_REDUCER_H0_CAPABILITY_V1`

This is a host-only implementation. It creates no D1 approval, arm, run
directory, D0 result, fresh-baseline success receipt, ready/run manifest or
device authority. The current Process-v2 integration remains blocked on
`FRESH_BASELINE_MISSING`.

## Bound inputs

The capability binds an internal H0 baseline-design identity containing the
exact S22+ target/profile, reducer source, D1 design source, and current common
D0 runtime. The active P3.19 candidate intent and qualification at
`candidate-qualification-v1-20260821-10` remain a separate private current-
candidate identity; no public Process-v2 manifest is created by this unit. The
current P3.19 stock Carrier adapter
`s22plus_fyg8_p319_stock_process_v2_adapter.py` and its full-retained-raw
classifier remain bound below.

The D1 design records one fixed normal-reboot path and one fixed approval-arm
path, but contains no arm writer or live implementation. Its explicit stub
raises before any effect. The host rehearsal covers only schema-level one-
reboot accounting; it does not create durable D1 state or prove a live arm.

## Producer and reducer contract

The D0 acquisition contract is recorded as a future boundary only. No D0
producer is present in this H0 unit. Before activation, a separately reviewed
producer must use the current raw-first runtime, read exactly 2,097,136 bytes
from `/proc/last_kmsg`, persist stdout and its capture receipt before invoking
the P3.19 classifier, and require exact target, boot/partition health and zero
Download endpoints at both edges. A non-clean result must publish a typed stop
receipt rather than disappear.

The reducer additionally binds the exact D1 action string, top-level and
binding journal objects, fixed arm/start/result paths, start-before health, and
the common D0 host-tool receipt shape and SHA fields. It accepts no approval or
unchecked replay-proof claim. D1 selected serial/topology must equal the sole
D0 target row.

The reducer (which is executable against host fixtures) reopens and validates
the D1 result plus arm/start journals, the D0 result plus raw-capture handle
and stdout bytes, the internal baseline design, the current candidate
intent/qualification, and the live P3.19 classifier. It cross-links returned
boot identity, target serial/topology, partition health and Download absence.
The published `fresh-baseline-v1` record is accepted by integration only when
it is byte-identical to a fresh reduction of those fixed inputs and its
identity is unchanged across integration validation; summary booleans or a
hand-written JSON cannot clear `FRESH_BASELINE_MISSING`.

The raw fact is named `candidate_marker_family_absent`; it is distinct from
the global consumed-candidate registry. The reducer's top-level
`device_contact=false` means the reducer itself is host-only, while nested D0
evidence must prove `device_contact=true`. The normalized result explicitly
sets `producer_execution_closure_reviewed=false` and
`producer_execution_closure_authoritative=false`; `validate_published_result`
therefore returns `authoritative=false`, and integration cannot clear the
fresh-baseline blocker.

## Hostile coverage

The focused tests cover baseline-design self-binding, one-reboot rehearsal,
deterministic reduction, hand-written boolean mutation, duplicate JSON keys,
wrong raw size/hash, candidate marker residual, D0 contact=false, fixed and
cross-bound D1 journal paths/content, D1/D0 serial and topology continuity,
the 437-source/73-module/EUD38/latch-only candidate closure, strict D0
host-tool identity, integration receipt-identity continuity, symlink and
hardlink raw evidence, no-clobber publication, and a source-level assertion
that both design modules contain no device-acquisition primitive. No test
invokes ADB, USB, Odin or a device.

The D1 and D0 live producers are intentionally hard-blocked in this H0 unit;
they do not contact a device or create an arm/run/intent. A follow-up must
first add a self-binding execution manifest, durable pre-contact intent and
typed stop-result owner, then obtain independent changed-closure review.
Independent review is required before changing the D1 review state or using
the D0 producer. The existing candidate requalification PASS_GO does not
qualify this new D1/reducer closure; any change to common Process-v2 evidence
registration or execution-critical source closure requires fresh
requalification and changed-closure review.

## Independent review

Independent changed-closure review first rejected foreign journal paths,
uncrossed D1/D0 identity, incomplete candidate closure, an overstated replay
self-test, a receipt TOCTOU window, and declarative approval/replay claims. The
final closure fixes or removes each of them. A later broad test also caught the
premature public candidate manifest because it violated the existing no-replay
audit; that manifest was deleted rather than exempted.

The final independent verdict is
`PASS_GO_P319_FRESH_BASELINE_REDUCER_H0_CAPABILITY_V1`. It qualifies only the
non-authoritative H0 reducer and the integration fail-open repair. The producer
execution closure remains mechanically unreviewed and non-authoritative, so
this PASS_GO cannot produce or validate a fresh baseline and does not clear
`FRESH_BASELINE_MISSING`. It grants no D0, D1, F1, recovery, replay, approval,
candidate result, device or live authority.
