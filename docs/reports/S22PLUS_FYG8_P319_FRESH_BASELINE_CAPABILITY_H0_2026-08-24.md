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

This paragraph records the topic-39 predecessor state. At that review point
the D1 file was design-only and raised before any effect. Topic 40 has since
implemented and independently reviewed a D1 producer with a self-binding
execution manifest, fixed approval-arm/run/stop paths and the reviewed P2.96
one-reboot state machine. That successor does not retroactively widen this
topic-39 PASS_GO. Its binding now records topic-40 capability `PASS_GO`, which
is not a current operator approval or run authority.

## Producer and reducer contract

The following sentence records the topic-39 predecessor boundary: no D0
producer was present in that H0 unit. Topic 41 now independently reviews the D0 producer.
Any separately authorized invocation must use the current raw-first runtime, read exactly 2,097,136 bytes
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
evidence must prove `device_contact=true`. The normalized result now explicitly
sets `producer_execution_closure_reviewed=true` and
`producer_execution_closure_authoritative=true`; `validate_published_result`
returns `authoritative=true` only after deterministic reopening of the exact
reviewed producer evidence. No current normalized fresh-baseline result exists,
so integration still cannot clear the fresh-baseline blocker.

## Hostile coverage

The focused tests cover baseline-design self-binding, one-reboot rehearsal,
deterministic reduction, hand-written boolean mutation, duplicate JSON keys,
wrong raw size/hash, candidate marker residual, D0 contact=false, fixed and
cross-bound D1 journal paths/content, D1/D0 serial and topology continuity,
the 437-source/73-module/EUD38/latch-only candidate closure, strict D0
host-tool identity, integration receipt-identity continuity, symlink and
hardlink raw evidence and no-clobber publication. The old assertion that both
producer files were non-acquiring describes only the predecessor: the
topic-40 D1 producer is now explicitly classified and byte-frozen by the
global acquisition detector. No test invokes ADB, USB, Odin or a device.

The immediate-failure D0 stub is the topic-39/40 predecessor. Topic 41 now
implements, independently reviews and registers the producer as an active
raw-first source. The topic-40 D1 successor
contains the self-binding manifest, durable pre-contact arm and typed stop
owner that this predecessor required and has its own independent capability
`PASS_GO`, but no current operator approval, arm or run exists. The existing
candidate requalification and topic-39 PASS_GO did not qualify topic 40; its
separate review did. Topic-41 review closes the joint D0/reducer closure, but
no actual combined result exists.

## Independent review

Independent changed-closure review first rejected foreign journal paths,
uncrossed D1/D0 identity, incomplete candidate closure, an overstated replay
self-test, a receipt TOCTOU window, and declarative approval/replay claims. The
final closure fixes or removes each of them. A later broad test also caught the
premature public candidate manifest because it violated the existing no-replay
audit; that manifest was deleted rather than exempted.

The final independent verdict is
`PASS_GO_P319_FRESH_BASELINE_REDUCER_H0_CAPABILITY_V1`. Topic 41 later adds
`PASS_GO_P319_D0_FRESH_BASELINE_H0_CAPABILITY_V1` for the exact producer and
joint reducer closure, so both `producer_execution_closure_*` fields are true
for a deterministically reconstructed hypothetical result. Capability review
is not a current operator approval; with no published fresh result, integration
still reports `FRESH_BASELINE_MISSING`. It grants no ready, D0, D1, F1,
recovery, replay, candidate result, device or live authority.
