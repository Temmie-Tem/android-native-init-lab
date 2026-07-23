# S22+ FYG8 P2.47 gate-range focused audit H0

Date: 2026-07-24 KST
Tier: H0 host-only
Status: `PASS_P247_GATE_RANGE_FOCUSED_AUDIT_H0`
Device contact: none

## Scope

This audit follows the P2.46 live progress record at `0x82,item=7`. It checks
only the P2.44/P2.45 8-to-12 gate expansion and the paths that can make a later
checkpoint unrecordable:

- generated plan, runtime, checkpoint client, kernel patch, decoder, and model;
- focused P2.44/P2.45 tests;
- both reproducible P2.45 kernel artifacts; and
- the Full-LTO `s22_fyg8_e1_write` implementation in the final `vmlinux`.

It performed no build, image construction, device contact, Download transition,
Odin invocation, or device write.

## Findings

### MUST-FIX: kernel item-index range remained at eight gates

The 12-gate expansion is correct everywhere except the kernel request
validator:

| Layer | Exact result |
|---|---|
| Plan | 12 ordered gates, `hwspinlock` through UDC |
| Runtime | gate count 12, stage end `0x86`, 11 driver basenames plus UDC |
| Checkpoint client | next-stage and item-index validation through `0x86` |
| Decoder/model | 80 stages; gate items 0 through 11 |
| Kernel sequence | 80 bytes; tail `0x80..0x86,0x8f` |
| Kernel request validator | gate item range still capped at `0x82` |

The P2.44 generator changed the kernel sequence tail but did not change the
second 8-gate assumption in the same historical patch:

```c
if (request->stage >= 0x7b && request->stage <= 0x82)
        expected_item = request->stage - 0x7b;
```

The exact P2.45 generated patch has SHA256
`1c9dc15b6bc19575cdd413487b610f1f2b4152a7c3bdb504dc90cbb95ab88be2`.
Its sequence contains all 80 expected stages, while its only provider
item-range upper bound is `0x82`.

Both clean P2.45 builds produced the same `vmlinux`, SHA256
`6d196356b653b613e004d71e4390163546e0390eea9b812a9dbc62809fa97a43`.
The linked `s22_fyg8_e2_sequence` is 80 bytes and ends with:

```text
80 81 82 83 84 85 86 8f
```

Full LTO inlined `s22_fyg8_e1_request_allowed()` into
`s22_fyg8_e1_write`. The final disassembly subtracts `0x7b`, compares the
offset with `#0x8`, and selects it only when unsigned-lower. That implements
offsets 0 through 7 and proves that the source defect reached the flashed
binary.

The sequence check remains an exact allowlist. If a normal next
`stage=0x83,item=8` request is submitted, the stale item validator must reject
it and the proc writer must return `-ERANGE`. The P2.46 retained record proves
only `0x82` success and no later stored outcome; it does not prove that this
particular boot submitted the rejected request.

### COVERAGE GAP: existing checks validated only one of two assumptions

The P2.44 patch transformation had two 8-gate assumptions:

1. the kernel E2 sequence ended at `0x82`; and
2. the kernel item-index range ended at `0x82`.

Only the first was transformed and checked. The source checker validates the
80-stage sequence, while the linked checker validates call ordering and cache
flushes but not item-index semantics.

The focused P2.44/P2.45 suite ran 20 tests in 84.027 seconds and passed. This
is expected under the current coverage and confirms that the defect is not
guarded by an existing test.

### SHOULD-FIX-BEFORE-NEXT-F1: prior-gate regression is unrecordable

The runtime rechecks every previously completed gate before checking the next
one. If an earlier predicate disappears, it calls `fail_at()` with that
already-completed stage. The checkpoint client permits only the next monotonic
stage, rejects the earlier stage locally, and `fail_at()` then parks without a
new record.

This is not proven as the cause of P2.46's stop. It is a separate
source-confirmed telemetry gap that can reproduce the same durable shape:
last progress present, no terminal outcome. It should be resolved or explicitly
accepted before spending another Full-LTO build and F1 cycle.

No other 8-gate constant was found in the generated plan, runtime, checkpoint
client, decoder, model, or kernel patch. Gate paths, module order, timeout,
evidence bytes, and transport do not need to change.

## Validator Design

The next validator should not replace `0x82` with another manually maintained
upper bound or a generous fixed superset. The exact sequence is already the
stage allowlist; item indices should be derived from its ordinal:

1. require the request stage to equal the exact next sequence element;
2. find the module-start and gate-start ordinals in that sequence;
3. derive module items from `ordinal - module_start`;
4. derive provider and later nonterminal items from
   `ordinal - gate_start`; and
5. keep local and terminal stages at item zero.

For the current sequence this derives:

```text
sequence count                 80
local stages                    8
module start ordinal            8
module count                   59
gate start ordinal             67
provider/USB gate items      0..11
terminal ordinal               79
```

Appending a future rung to the exact sequence then updates its expected item
without another parallel range edit. If E3/E4 needs different item semantics,
it must use a new explicit profile/sequence contract rather than inheriting an
arbitrary superset.

This still requires one new kernel build: the currently linked compare against
eight cannot be changed from userspace. It should be the last build caused only
by this validator's duplicated upper bound.

## Next Bounded Unit

P2.48 is H0 implementation:

1. preserve all historical P2.44/P2.45 bytes;
2. add one versioned source-contract adapter that changes only the kernel
   expected-item derivation;
3. decide and encode one bounded outcome for prior-gate regression before the
   candidate build;
4. add mutation tests that fail on an 8-gate validator and pass when an exact
   sequence gains a synthetic later nonterminal stage;
5. extend the linked audit to verify the final Full-LTO validator semantics,
   not only its call and flush sequence;
6. run the existing P2.44/P2.45 regressions plus the new focused tests; and
7. obtain one independent review of the changed execution-critical closure.

Do not build or prepare another live candidate until that H0 closure passes.
