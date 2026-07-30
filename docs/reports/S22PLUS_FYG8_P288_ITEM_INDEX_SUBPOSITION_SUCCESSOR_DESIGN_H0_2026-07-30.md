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
not multiply the record capacity by 256. More importantly, `generation` is not
a free-running publication counter. It is the one-based index of the exact
declared position sequence.

The historical model makes that binding explicit:

```text
_stage_generation(profile, stage) = _sequence(profile).index(stage) + 1
apply_request() requires request.stage == sequence[active.generation]
```

Consequently a second publication with the same stage and a different item is
rejected by the historical contract. The stage-only `.index()` lookup would
also silently select the first occurrence if a duplicate stage were inserted.
P2.88 must not modify that historical model. It needs a versioned position
model whose sequence elements are exact `(stage, item_index)` pairs.

P2.86's sequence length and terminal generation are both 92. P2.88's sequence
length and terminal generation are both exactly 103. The meaningful upper
bound is therefore `len(POSITION_SEQUENCE) == 103`, not “152 spare generation
values.” The one-byte representation remains a compile-time size guard, but
no accepted P2.88 transition exists beyond position 103.

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

The versioned host model must replace every stage-only position operation with
pair-aware equivalents:

- `generation_for_position(stage, item_index)`;
- exact-next comparison in `apply_request()`;
- pair uniqueness rather than stage uniqueness;
- a terminal position `(0x93, 0)` in addition to the compatible terminal stage
  byte;
- terminal success requiring the exact terminal generation and pair; and
- decoder validation of generation, stage, and item together.

Historical P2.32/P2.45/P2.86 records and decoders remain untouched.

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
checks their control-flow order and exact cardinality.

The runtime API is stricter than passing the generated stage and item back to
the client. A P2.88 publication names a symbolic position. The checkpoint
client uses its current generation to obtain the exact next stage/item pair
from the generated descriptor table. The runtime cannot choose those two wire
fields. The symbolic label must equal that same next descriptor ordinal.

Thus a source-order mistake cannot write a plausible but false location:

1. the label/ordinal mismatch is rejected before the requested progress write;
2. the fallback publisher derives the real next pair from the client
   generation; and
3. it publishes the reserved `unclassified` terminal failure at that real
   position before parking.

The source gate independently extracts the named publication calls from the
actual runtime functions, follows the declared success-path call order, and
requires exact equality with the ordered position declarations. Mutation
fixtures remove, duplicate, reorder, and rename one call each. All must fail.
Lexical presence alone is insufficient.

The generated contract rejects:

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

## Silence-park invariant

P2.88 adds a source and control-flow invariant:

```text
no raw quiet_park() is callable except through the evidence-park primitive
```

Every one of the 16 P2.86 local park sites is assigned exactly one successor
route:

- statically unreachable under the bound input/state contract;
- immediately preceded by an exact successful failure/success publication; or
- immediately preceded by an attempt to publish the reserved `unclassified`
  failure at the descriptor-derived next position.

The generated runtime contains one raw park primitive. All inherited and local
call sites are routed through checked wrappers. Classification functions that
return zero or a structurally inconsistent result cannot park directly; they
publish `unclassified` first. Publication-call failure retains the immediately
preceding committed position, while a sequence-label failure gets an
`unclassified` publication at the actual next position. The generation-zero
kernel ENTRY record remains the fail-closed floor before the first userspace
publication.

A static park-route table names every site and its dominating publication.
The gate fails for an unlisted park, a direct raw-park call, a park whose
publication edge was removed, or a classifier-zero path without the reserved
route.

Terminal immutability and generation exhaustion are not new mechanisms:

- an accepted terminal outcome already prohibits later publication; and
- `generation >= len(POSITION_SEQUENCE)` already rejects advancement, so u8
  wrap cannot occur.

P2.88 gates the stronger statement that every successful control-flow path
ends at generation 103 and no path can request a 104th position. A malformed
attempt at the terminal boundary is handled by the same descriptor-derived
`unclassified` failure route rather than being misdescribed as u8 wrap.

## Decoder multiplicity and evidence-layer closure

The repeated positions do not change boot multiplicity. The three historical
classifiers compute `minimum_candidate_boots` from the number of independent
45-byte long records plus exact UNSAT records. They do not count slot
generation or the two committed slots as boots.

P2.88 nevertheless versions the evidence-selection closure and adds focused
fixtures:

- one 45-byte record containing adjacent `(0x90,0)` and `(0x90,1)` slots must
  report one minimum candidate boot;
- two independent records must report two;
- a torn-slot fallback remains one record and one boot; and
- the Device Action F1 evidence adapter must pass through the selected P2.88
  decoder result without deriving multiplicity from generation.

`device_action_f1_evidence_v2.py` currently imports the P2.86 selector and has
P2.86-specific stock-closure and candidate-static branches. Decoder selection
alone is therefore insufficient. P2.88 support must include that typed evidence
layer and its stock-closure/static-schema dispatch. This tooling is not a
boot-byte input, but it must be approval-bundle-bound and independently
reviewed before any later F1.

## Inherited `0x8e/detail=0` check

The suspected P2.86 mismatch is not present in the checked source. A focused
fixture encoded generation 87 as:

```text
stage=0x8e outcome=progress item_index=0 detail=0
```

Both `s22plus_fyg8_p286_contract_spec.validate_slot()` and the exact P2.86
decoder accepted it, and the P2.86 post-F1 report independently decoded the
same tuple as valid. It is ordinary zero-detail progress, not an exact
diagnostic-detail row. P2.88 carries this prefix position unchanged and adds a
regression fixture so the issue cannot be reintroduced.

## Build-layout leak gate

P2.88 remains subject to the P2.86 private clang-resource path incident. The
new candidate build cannot infer reproducibility from source receipts alone.
After Full-LTO A and before starting B, the procedure must scan `vmlinux` for:

- the random private namespace prefix; and
- absolute host/tmp clang resource paths.

Both counts must be zero, and the stable mapped toolchain path must be present.
Failure stops the pair before B. A future depth-independent mapping is a
candidate-byte change and belongs in a separately frozen P2.88 build input;
until selected and implemented, the proven real-directory relocation remains
the required build-host layout.

## Explicitly excluded scope

The regulator predicates from the HSPHY paper design are not part of P2.88.
They would add sysfs reads, new blocking boundaries, new failure routes, and a
different proof objective. P2.88 is limited to making the existing restart,
readback, trace, bind, and final-sampling path attributable.

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
The same exclusion applies to reports, selector/retirement registration,
decoder adapters, typed-evidence adapters, static checkers, linked auditors,
freeze reports, and qualification reports. They must not be added to
`SOURCE_KEYS` merely because they validate the candidate. Each P2.88 key must
have a demonstrated boot-byte influence or be an inherited payload input.

Intent derivation is forbidden until:

- the exact position table above is implemented and no unbounded boundary is
  silently added between named positions;
- terminal generation equals the exact 103-position sequence length on every
  success path;
- the pair-aware model, client, kernel validator, decoder, and typed evidence
  adapter agree;
- runtime publication call order equals declaration order under the static
  success-path gate;
- every park site is unreachable or publication-dominated and no classifier
  zero path parks silently;
- the active producer-route equality gate passes;
- `c57/c58/c59/c5c` have zero active routes;
- the known-good prefix through generation 88 is byte-semantically unchanged;
- decoder, userspace client, and kernel validator reject all position
  mutations; and
- one-record/two-slot evidence remains one inferred candidate boot;
- `0x8e/detail=0` remains a valid inherited progress tuple;
- the Full-LTO A-before-B private-path leak gate is part of the build
  procedure; and
- the new SOURCE_KEYS are printed and compared with a clean Git state.

No device step is authorized by this selection.

## Host evidence

This H0 used only tracked source and retained private build products.

- P2.86 exact source receipts remained `70/70`, with `CHANGED_KEYS=[]`.
- P2.86 terminal generation and sequence length are both 92.
- A standalone layout check packed CRC-valid repeated stage `0x90` values
  with adjacent generations and distinct item indices while preserving the
  exact 45-byte record and 10-byte slots. A pair-aware validation callback
  accepted generation 89 `(0x90,0)` followed by generation 90 `(0x90,1)` and
  rejected generation 90 with the stale item 0. The current historical
  decoder correctly rejects that new semantic until its position-aware
  successor exists.
- A direct P2.86 fixture verified generation 87
  `(0x8e,progress,item=0,detail=0)` is valid.
- The exact P2.86 trace descriptor has 16 cycle events and 6 bind events;
  their existence does not make dynamic per-iteration generation consumption
  acceptable.
- The existing reachable-record check passed while demonstrably consulting no
  production source.

No compiler, kernel build, image build, device connection, transfer, reboot,
or live action was performed.
