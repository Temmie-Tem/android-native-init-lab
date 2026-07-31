# S22+ FYG8 P2.92 accept-to-resume and Stage C H0

Date: 2026-07-31 KST

Verdict:

- `PASS_P292_ACCEPT_TO_RESUME_AND_ERRNO_CLOSURE`
- `PASS_P292_STAGE_C_IDENTITY_MUTATION_MATRIX`

Scope: host only. No kernel image, boot image, AP archive, intent, device
connection, live approval, or F1 action was created or used.

## Question

Does the repaired checkpoint channel continue from every accepted
nonterminal record, including the retained P2.90 generation-88 record, and
does a checkpoint publication failure remain attributable instead of becoming
silent? Can verifier, decoder, and evidence changes be separated from payload
identity without weakening downstream approval binding?

## Bound material

The gate regenerates the complete 13-artifact P2.92 repaired materialization
from the already-proven P2.90 zero-delta baseline and the attributed phase-2
repair. The repaired materialized `candidate.patch` is 28,201 bytes with
SHA256
`65f30fd2843510bc4437b8155b512dff4b806d68f0f32f891024cb166fb7e72b`.
The phase-2 repair SoT descriptor SHA256 is
`68ad5fcb719f65ec3fbf1f18279b72ddbf428fdbbcffe0327ef40e76b07b14aa`.

The host harness extracts the production kernel writer from that patch. It
does not reimplement the writer algorithm. The OF-only retained-log locator is
replaced by a fixed host buffer; record layout, CRC, request validation,
active-slot comparison, three-step commit, state update, seed initialization,
and error returns remain the materialized production source.

The exact materialized userspace checkpoint client is compiled separately
with only its three raw syscalls replaced by deterministic capture/fault
stubs. A third harness extracts the exact runtime errno/park wrapper and
replaces only the final raw park with `longjmp`, so evidence written before
park is inspectable.

## `ACCEPT_TO_RESUME_CLOSURE`

The gate enumerates 171 accepted nonterminal active states:

- generation zero ENTRY;
- every declared nonterminal position through generation 106; and
- every progress detail allowed at each position, including the inherited
  zero-detail path and all nonzero warning details.

For every state it constructs the exact committed active slot, initializes the
repaired kernel state from those bytes, submits the exact declared successor,
and requires a 32-byte successful write and generation advance. The Python
model and decoder independently decode the same active state, apply the same
request, and require the same next generation.

Two corruption controls flip either the retained active detail byte or its
CRC while leaving the kernel's exact expected slot unchanged. Both return
pre-mutation `-ESTALE`; neither record nor state advances. This proves the
repair did not weaken the byte-exact active-slot guard.

## `ACCEPT_TO_RESUME_SEQUENCE_WALK`

The production kernel writer continuously walks all 107 positions twice from
seed through terminal:

1. the live-prefix path, including generation 88
   `(stage=0x8f,outcome=PROGRESS,item=0,detail=0xc18)`; and
2. a producer-derived diagnostic path with consecutive nonzero
   `detail=0xc01` records at generations 87 and 88.

The consecutive detail is not a hand-selected decoder-only value. The
materialized trace descriptor declares `0xc01/PROGRESS/stage-mask=0x0e`, and
the runtime routes both STOP (`0x8e`) and SUSPENDED (`0x8f`) classification
warnings through `p282_publish_classification`.

The two walks produce 214 retained snapshots. Every snapshot is byte-identical
to the P2.92 Python model and decodes to the exact generation, stage, item,
outcome, and detail. State, retained record, and model are not reinitialized
within a walk. A fresh local file position is used for each write because the
production client opens a new proc descriptor for every publication; this is
the real runtime file-lifetime model, not a state reset.

After terminal, another write returns `-EALREADY`.

## Existing retained state and seed path

Two separate controls cover the current device initial condition without
contacting a device:

1. An exact P2.90 record with valid generation 87 and generation 88
   `detail=0xc18` slots initializes repaired writer state. The next
   `(0x8f,item=1)` request commits generation 89.
2. The same old record is placed elsewhere in the retained ring before the
   repaired `record_entry("/init")` path runs. The old bytes remain intact,
   the new candidate seed becomes ready at generation zero, and its first
   request commits generation one.

Thus the repaired candidate neither repeats the inherited `-ESTALE` defect nor
silently fails at generation zero merely because the current retained ring
contains P2.90 evidence.

## `CHECKPOINT_ERRNO_OBSERVABILITY`

The materialized client continuously emits all 107 canonical requests. Its
captured 3,424 request bytes are byte-identical to the model.

Four injected syscall failures prove exact operation and errno preservation:

- `openat=-2`;
- `write=-116`;
- short write, normalized to `write=-EIO`;
- `close=-9`.

Each leaves client generation unchanged, exposes the exact operation/errno,
then emits one operation-aware terminal failure request with the corresponding
`0x4xxx`, `0x5xxx`, or `0x6xxx` detail. Kernel writer, model, and decoder all
accept and decode representative open/write/close details.

The runtime-wrapper harness separately proves:

- successful fallback parks only after the failure request returns success;
- primary plus fallback failure stores trigger rc, operation, exact errno, and
  fallback rc in the volatile sink before raw park; and
- failed inspection plus failed unclassified fallback also reaches that sink
  before park.

This does not claim that total checkpoint-channel failure can durably report
through the failed channel. It proves that the exact errno is not discarded
and that the final non-durable branch is explicit and inspectable.

## `CHECKPOINT_SOT_COHERENCE`

One P2.92 repair descriptor supplies the 107 position pairs, exact-slot state
representation, publication operations, and errno-detail ranges. The
materialized kernel writer and client are generated from it; the versioned
P2.92 model and decoder consume the same semantics. The kernel snapshot and
client request byte comparisons close the gap between a declared table and
the code that actually writes it.

This follows the completed ordered migration:

1. phase 1 reproduced the frozen P2.90 materialized baseline byte-for-byte
   before checking run-A/run-B determinism; and
2. phase 2 changed exactly the five predeclared repair artifacts and left the
   other eight byte-identical.

No equality condition was weakened.

## P2.64 Stage C identity split

The authoritative P2.92 descriptor produces three disjoint receipt sets:

- Tier 1: payload identity. It contains 68 inherited payload keys, six direct
  P2.92 SoT/generator/repair inputs, and all 13 generated payload artifacts.
- Tier 2: qualification/provenance. It contains 26 inherited
  decoder/audit/stock-closure/evidence keys plus the P2.92 verifier, decoder,
  tests, and reports.
- Tier 3: package/live closure. It contains Process-v2 runner, evidence
  parser, and process contract receipts; candidate AP, rollback AP, manifest,
  and target profile are dynamic receipts.

The generated payload receipts remain Tier 1 even when their source is a
Tier-2 verifier. Therefore a nominal Tier-2 change that actually changes a
materialized payload still changes payload identity.

The seven mutation lanes prove:

- a Tier-1 byte changes payload, qualification, and live identities;
- a Tier-2 verifier or documentation byte leaves payload identity unchanged
  but changes qualification and live identities;
- a Tier-2-originated generated-payload change changes all three identities;
- a Tier-3 runner byte changes only live identity;
- candidate AP or manifest bytes change live identity;
- duplicate or unassigned paths fail closed; and
- stale qualification and package closures are rejected.

This is the first conservative P2.64 Stage C implementation. It is not yet
closed: the required independent safety review remains pending, and final
P2.92 source-contract/build/package inputs must be added to Tier 1 before
intent.

## Interpretation boundary

This H0 restores and proves the observation channel. It does not advance the
E3 device frontier: `0x8f` and every later live boundary remain unknown.

The four prior identical generation-88 records remain the stable prefix
baseline. Any successor divergence before that tuple is a new regression.
If a closure-proven successor again becomes silent after `0x8f`, stop adding
code-position markers and test coupling to the parent-suspend/PHY-power system
state instead. That interpretation rule survives the withdrawn child-observer
proposal.

No new S22+ F1 is authorized.
