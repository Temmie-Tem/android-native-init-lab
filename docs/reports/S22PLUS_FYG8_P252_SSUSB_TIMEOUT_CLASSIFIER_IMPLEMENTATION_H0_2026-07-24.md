# S22+ FYG8 P2.52 SSUSB Timeout Classifier Implementation (H0)

Date: 2026-07-24 KST
Tier: H0 host-only
Status: `PASS_P252_SSUSB_CLASSIFIER_IMPLEMENTATION_HOST_ONLY`

## Scope

P2.52 implements the bounded discriminator designed after P2.50 stopped at:

```text
stage=0x84 item_index=9 detail=110
```

This unit changed only versioned host source-generation, decoder, selector,
and test code. It did not build a kernel, image, or candidate; contact a
device; invoke Odin; or authorize F1.

## Implementation

The new contract adds:

```text
s22plus_fyg8_p252_contract_spec.py
s22plus_fyg8_p252_e1_decoder.py
s22plus_fyg8_p252_source_contract.py
```

and one registration in `s22plus_fyg8_source_contracts.py`.

The P2.52 specification is the sole executable definition of:

- 15 ordered exact sysfs driver-bind paths;
- each expected symlink target basename;
- exact failure details `0xa01..0xa0d`, `0xa20..0xa21`, `0xa10`, and
  `0xa30`;
- SSUSB stage `0x84`, item/gate index `9`;
- the exact `waiting_for_supplier` path; and
- the five-second one-shot grace.

That descriptor generates the userspace bind table, userspace checkpoint
whitelist, kernel whitelist, decoder semantics, linked-table expectations,
and mutation-test expectations. There is no broad accepted `0xaXX` range.

The source adapter delegates `p248.generate()` and applies three
count-checked transformations:

1. the runtime classifies only the SSUSB timeout at the existing global
   20-second deadline;
2. the userspace checkpoint accepts positive structured detail only through
   the exact stage/detail validator; and
3. the kernel writer dispatches the `0x8XX` and `0x9XX` bands before the exact
   classifier whitelist, so `0xa30` is not interpreted as gate index 48.

The P2.48 80-step sequence, 59-module plan, 12 gates, terminal stage `0x8f`,
record layout, and raw decoder `active` object are unchanged.

## Runtime Semantics

At the SSUSB timeout only, the generated runtime:

1. revalidates prior gates `0..8`;
2. rechecks the SSUSB parent;
3. parses exact `0\n` or `1\n` plus EOF from `waiting_for_supplier`;
4. evaluates 15 exact symlinks in descriptor priority order;
5. rechecks the parent and waiting attribute;
6. either records the first exact missing bind, records `0xa10`, or enters
   one five-second grace; and
7. performs a full exit rescan before recording `0xa30`.

All classifier terminal paths pass one common finalizer that first revalidates
prior gates and then rechecks the parent. A concurrent parent bind therefore
wins over a proposed classifier failure. Prior-gate regression remains
recorded at the monotonic frontier `0x84`.

The original 20-second deadline is not reset. If SSUSB binds during grace,
the existing gate loop resumes without granting downstream gates another
20-second budget. It drains already-bound downstream gates without waiting
and records timeout only after it has actually checked the first absent gate.

## Static Evidence

The implementation result proved:

- the 15-path map equals the P2.51/P2.51b audit output;
- P2.48 generation remains unchanged;
- the P2.44 plan header is byte-identical;
- the transformed kernel patch applies cleanly;
- two static AArch64 userspace links are byte-identical;
- only the 17 exact new details are accepted, only at stage `0x84`;
- all other `0xa00..0xfff` values are rejected at every stage;
- every reachable slot variant, including all 17 classifier details, decodes
  without changing the raw active-slot shape;
- mutations to path, basename/detail table, grace duration, strict waiting
  parser, final rescan, common finalizer path, post-grace drain state,
  checkpoint whitelist, or kernel whitelist are rejected; and
- the final linked-audit interface now requires the retained
  `writer -> request validator -> item/detail validators` call chain and
  `READ_ONCE` loads from both exact classifier tables.

## Independent Review

The first independent review returned `NO-GO` on two findings:

1. after grace success, an already-bound DWC3 gate could advance and the
   expired deadline could record UDC timeout before UDC had been checked; and
2. the linked audit modeled a direct writer-to-detail call instead of the
   source's request-validator chain and could lose table loads to Full-LTO.

Both findings were fixed before commit. The runtime now tracks progress after
classifier success and performs a zero-wait downstream drain. The kernel patch
retains both validators as `noinline __used`, uses `READ_ONCE` for exact table
loads, and the linked audit follows the actual call graph. The independent
fix-only re-review found no remaining blocking issue and returned `GO` for the
P2.52 H0 implementation.

Focused validation:

```text
14 P2.52 tests                         PASS
19 P2.45/P2.48 regression tests       PASS
34 candidate-build/Process v2 tests   PASS
py_compile                            PASS
git diff --check                      PASS
```

The userspace result is an AArch64 statically linked ELF and repeated links
were byte-identical.

## Proof Limit

The classifier produces a bounded observation coordinate, not a permanent
root-cause verdict.

- `0xa01..0xa21` means the corresponding exact bind was absent at the
  classification snapshot.
- `0xa10` means every enumerated bind passed while the exact waiting attribute
  still reported one.
- `0xa30` means the entry and exit dependency snapshots passed while the
  parent remained absent at every grace poll.

`0xa30` does not prove that all nested binds stayed continuously present
between the two snapshots. A different result across runs is itself evidence
for a timing-sensitive branch. The five-second grace is a bounded settling
window, not proof that all possible late probes have completed.

## Safety

```text
host_only=true
kernel_built=false
image_built=false
candidate_created=false
device_contact=false
device_write=false
odin_invoked=false
live_authorized=false
```

No current F1 authority or reusable binding exists.

## Decision

`PASS` for the P2.52 H0 implementation closure.

The next separate H0 unit is the final Full-LTO build and linked audit. It must
verify the exact classifier table bytes and writer-to-validator dataflow in
`vmlinux` before any candidate promotion or connected preparation. This
implementation report does not authorize that later device action.
