# S22+ FYG8 P2.88 item-index subposition successor design H0

Date: 2026-07-30 KST

Status:
`PASS_P288_ITEM_INDEX_SUBPOSITION_SUCCESSOR_SELECTED_H0`

## Verdict

P2.88 should combine the cheap early-snapshot removal with a finite,
source-generated `item_index` subposition sequence. Sending the snapshot-only
minimum successor first is rejected.

Both choices already require a new contract, intent, Full-LTO A/B pair,
package/static closure, ready manifest, D0, and fresh F1 approval. The
item-index design adds checkpoint transition, decoder, and validator work, but
does not add another build pair, another retained byte, another slot, or a
device action. In return, it prevents a third F1 silence from collapsing every
post-helper blocking boundary into one observation.

The selected design preserves:

- the 45-byte retained record;
- two 10-byte A/B slots;
- the existing slot CRC and torn-write commit protocol;
- the numeric stages `0x8d..0x93`;
- the exact known-good prefix through generation 88,
  `0x8f/detail=0xc18`; and
- P2.86 as immutable historical evidence.

It changes the successor's position sequence after `0x8f`. Repeated stage
values are distinguished by an ordered, stage-local `item_index`.

This is a host-only paper design. No P2.88 source, selector, intent, image,
manifest, or live authority exists.

## Layout correction and usable capacity

The spare byte is real, but the slot-body field order needs one correction.
`s22plus_fyg8_p232_e1_latest_stage_design.py:105-106` defines:

```text
REQUEST_STRUCT   <4sBBBBHBB16sI>
SLOT_BODY_STRUCT <BBBBH>
```

The slot body is packed at `:294-299` as:

```text
generation / stage / outcome / item_index / detail
```

Profile is in the 25-byte record header, not in the slot body. The matching
kernel structure in the exact P2.86 patch has the same five fields.

`item_index` is therefore available for local-stage subpositions, but it does
not multiply the record capacity by 256. `generation` is also one byte, is
bound to slot parity, and orders the two retained slots. The whole boot has at
most 255 committed generations.

P2.86 has:

```text
step count              92
terminal generation     92
remaining u8 headroom  163
```

The finite sequence below ends at generation 103 and leaves 152 unused
generation values. There is no wrap case to support. A successor must reject
at generation time, build time, and decoder initialization time if its
position count exceeds 255.

## Why the current API cannot merely receive a nonzero index

The byte and request field are wired, but same-stage advancement is currently
forbidden in three independent places:

1. userspace `publish()` requires
   `e1_next_stage(client->stage) == stage`;
2. userspace `valid_item_index()` requires zero for local stages; and
3. the model and decoder require
   `generation == ordinal_for_stage(stage) + 1`, assuming each stage appears
   once.

The kernel independently indexes the exact stage and item tables by current
generation and rejects any request whose pair differs. Thus changing only
`0U` at the call site would fail closed; it would not publish a subposition.

The useful fact is that the kernel's sequence and item tables are already
ordinal-indexed. A successor can safely contain duplicate stage bytes if it
defines one exact ordered sequence of `(stage, item_index)` pairs and makes all
four implementations consume that same sequence:

- userspace checkpoint client;
- kernel request validator;
- retained-record decoder/model; and
- linked/static auditors.

## Frozen minimum position sequence

The prefix through generation 88 remains byte-semantically unchanged. The
successor begins subpositions only after the proven parent-suspended record.

Each result position has two possible uses:

- failure: publish the exact failure and become terminal; or
- success: publish zero-detail progress immediately before the next possibly
  blocking operation.

Consequently the presence of the next position proves that the preceding
operation returned and satisfied its required postcondition.

| Generation | Stage | Item | Progress meaning / next boundary |
|---:|---:|---:|---|
| 88 | `0x8f` | 0 | unchanged parent-suspended classification |
| 89 | `0x90` | 0 | PERIPHERAL helper dispatch begins |
| 90 | `0x90` | 1 | helper returned zero; child-active read begins |
| 91 | `0x90` | 2 | child active matched; parent-mode read begins |
| 92 | `0x90` | 3 | parent peripheral matched; exact-UDC read begins |
| 93 | `0x90` | 4 | exact UDC matched; restart-worker refresh begins |
| 94 | `0x90` | 5 | refresh returned; final cycle capture begins |
| 95 | `0x90` | 6 | capture returned; restart classification begins |
| 96 | `0x90` | 7 | restart classified; cycle trace cleanup begins |
| 97 | `0x91` | 0 | cycle cleanup returned; bind trace setup begins |
| 98 | `0x91` | 1 | bind setup returned; configfs UDC bind begins |
| 99 | `0x91` | 2 | UDC bind returned; bind trace finish begins |
| 100 | `0x91` | 3 | bind trace finished and bind result classified |
| 101 | `0x92` | 0 | final state/speed sampling begins |
| 102 | `0x92` | 1 | final state/speed result classified |
| 103 | `0x93` | 0 | unchanged terminal success |

This is the minimum source-complete table selected for implementation. It
marks logical blocking call boundaries, not every iteration inside a bounded
poll loop. The loop count must remain bounded by its existing deadline. A
future implementation may split one logical call, such as final capture, only
before intent and only by inserting another named position into this single
table.

Examples of retained interpretation become:

```text
0x8f/0 + 0x90/0  -> parent gate passed; helper was dispatched but item 1
                    was never committed
0x90/0 + 0x90/1 -> helper returned zero; child-active read did not advance
0x90/1 + 0x90/2 -> child active matched; parent-mode read did not advance
0x90/6 + 0x90/7 -> classification completed; cycle cleanup did not advance
0x91/1 + 0x91/2 -> UDC bind returned; bind trace finish did not advance
```

The last two slots are enough because the positions are totally ordered. No
raw-ring headroom calculation or slot expansion is needed.

## Helper classification changes

The two early restart snapshots remain removed:

- no pre-dispatch `p282_cycle_refresh()` and no frozen
  `residual_outer_open`; and
- no immediate post-helper refresh and no helper
  `start_entered/start_returned` enrichment.

The bounded helper is classified from parent-owned fields first. At
`(0x90, 1)`:

- dispatch failure, unreaped child, malformed completion, returned write
  error, and generic helper timeout are exact failures;
- successful complete zero return is zero-detail progress; and
- the progress record is emitted before child-active, parent-mode, UDC, or
  trace reads.

The no-trace timeout receives a new versioned semantic,
`peripheral-helper-timeout`. It must not be called a flush timeout.

The active P2.88 producer domain explicitly retires:

- `0xc57/peripheral-flush-timeout`;
- `0xc58/residual-outer-tail-timeout`;
- `0xc59/start-peripheral-no-return`; and
- `0xc5c/restart-trace-cleanup-pending`.

The first three lost their trace evidence sources. The last is replaced by
the ordered `(0x90, 7)` cleanup-start position. P2.86's decoder and report
remain the authority for historical P2.86 records; P2.88 must not silently
reuse any retired value with a new meaning.

All later exact failures move to the result position immediately following
their operation. For example:

- child-not-active belongs to `(0x90, 2)`;
- completed write but non-peripheral readback belongs to `(0x90, 3)`;
- exact-UDC regression belongs to `(0x90, 4)`;
- restart trace/classifier failures belong to `(0x90, 6)` or `(0x90, 7)`;
- cycle-cleanup failure belongs to `(0x91, 0)`; and
- bind failures remain within stage `0x91`, at their exact item.

No failure after a progress position may be sent to an already-consumed
position. That would make the userspace client reject it and recreate silent
failure.

## Existing reachability gate is not a producer-reachability gate

The current function is named `validate_reachable_records()`, but it validates
the declared record domain rather than runtime production.

The exact function:

- accepts only `run_id`;
- obtains cases from `spec.failure_details(step)` and declared progress
  details;
- encodes each declared tuple;
- decodes it; and
- checks the resulting count.

It never reads the runtime include, classifier include, or a production
publish site. A focused call against the exact P2.86 run returned:

```text
signature                       (run_id)
reachable_slot_variants         177090
exact_diagnostic_detail_count   59
declared c57/c58/c59            all present
runtime/classifier source refs  none
```

Therefore deleting the three runtime evidence inputs while retaining the
three declarations would not be rejected by this gate. Synthetic classifier
fixtures also do not close the gap: they can construct observation states
that the production runtime no longer supplies.

P2.88 needs two differently named contracts:

1. `DECODABLE_RECORD_VARIANTS`: every tuple the decoder and kernel accept; and
2. `ACTIVE_PRODUCER_ROUTES`: every exact tuple the production runtime can
   publish, keyed by `(stage, item_index, outcome, detail)`.

The active route table is bidirectional:

- every active exact detail has at least one named production result branch;
- every exact production failure/progress branch is declared at its exact
  position;
- every zero-detail progress position is named;
- retired details have zero active routes; and
- a classifier-only fixture is not a production route.

Mutation tests must fail when a production route is removed while its detail
remains active, when a route emits an undeclared detail, or when
`c57/c58/c59/c5c` is restored to the active producer table.

## Mechanical numbering and validation

Subposition numbers must not be hand-maintained in runtime C.

One ordered `POSITION_SEQUENCE` in the successor contract spec is the single
source. It contains a stable symbolic name, stage, item index, and allowed
outcome/detail routes. Generators derive:

- kernel stage and item tables;
- userspace checkpoint transition tables;
- named C position constants;
- decoder position names and exact validation;
- linked-audit bytes; and
- active-producer coverage fixtures.

Runtime code refers only to named position constants. The source contract
checks their control-flow order and exact cardinality. The generated contract
rejects:

- duplicate `(stage, item_index)` pairs;
- non-monotonic item indices within a repeated local stage;
- skipped or repeated generations;
- a stored item outside the declared pair for that generation;
- a stage-only lookup where more than one position exists;
- more than 255 committed positions;
- a terminal outcome before the terminal position; and
- any advancement after a terminal outcome.

The decoder must select the active slot by adjacent generation as before, then
validate both stored `stage` and stored `item_index` against that generation's
declared position. Slot parity, CRC-zero commit, adjacent-slot fallback, and
terminal immutability tests remain unchanged.

## Successor scope and stop gate

P2.88 implementation must not begin by editing P2.86. It must create
versioned successor sources and freeze the complete change list before intent.
At minimum the candidate identity closure will include the successor:

- contract spec and source contract;
- checkpoint client transformation;
- kernel checkpoint request/sequence transformation;
- runtime and classifier includes;
- decoder policy inputs that affect the kernel accepted domain;
- userspace/build/packaging inputs inherited by the candidate; and
- generated position descriptor.

Verifier-only producer-coverage tooling may remain outside candidate identity
only if the approval bundle binds it and it cannot change `boot.img` bytes.

Intent derivation is forbidden until:

- the exact position table above is implemented and no unbounded boundary is
  silently added between named positions;
- terminal generation is statically below 256;
- the active producer-route equality gate passes;
- `c57/c58/c59/c5c` have zero active routes;
- the known-good prefix through generation 88 is byte-semantically unchanged;
- decoder, userspace client, and kernel validator reject all position
  mutations; and
- the new SOURCE_KEYS are printed and compared with a clean Git state.

No device step is authorized by this selection.

## Host evidence

This H0 used only tracked source and retained private build products.

- P2.86 exact source receipts remained `70/70`, with `CHANGED_KEYS=[]`.
- P2.86 terminal generation is 92 and u8 headroom is 163.
- A standalone layout check packed CRC-valid repeated stage `0x90` values
  with adjacent generations and distinct item indices while preserving the
  exact 45-byte record and 10-byte slots. The current decoder correctly
  rejects that new semantic until its position-aware successor exists.
- The exact P2.86 trace descriptor has 16 cycle events and 6 bind events;
  their existence does not make dynamic per-iteration generation consumption
  acceptable.
- The existing reachable-record check passed while demonstrably consulting no
  production source.

No compiler, kernel build, image build, device connection, transfer, reboot,
or live action was performed.
