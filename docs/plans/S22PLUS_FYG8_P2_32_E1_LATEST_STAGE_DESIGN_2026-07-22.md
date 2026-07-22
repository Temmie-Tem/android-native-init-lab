# S22+ FYG8 P2.32 compact E1 latest-stage design

Date: 2026-07-22 KST
Tier: H0, host-only design and executable model
Status: `PASS_P232_E1_LATEST_STAGE_DESIGN_HOST_ONLY`
Live authority: none

## Decision

Continue E1 with one 45-byte, frozen-cursor record containing a shared
candidate identity and two compact A/B checkpoint slots. This preserves the
only live-proven long-record geometry while retaining the prior valid stage if
an update tears.

Do not use a single mutable record. Commit-last alone cannot preserve its old
body after invalidation or a partial overwrite. Do not return to the unproven
173-byte carrier. The compact A/B record satisfies both constraints:

```text
8-byte family + 1-byte format/profile + 16-byte run ID + 2 * 10-byte slot
= 45 bytes
```

P2.32 defines no kernel patch, image, manifest, approval, or device action.

## Long Record Layout

All multibyte integers are little-endian.

| Offset | Size | Field | Rule |
|---:|---:|---|---|
| 0 | 8 | family | exact `S22E1L1|` |
| 8 | 1 | format/profile | high nibble format `1`; low nibble E1A=`1`, E1B=`2` |
| 9 | 16 | run ID | one nonzero manifest-bound 128-bit identity |
| 25 | 10 | slot A | even generation only |
| 35 | 10 | slot B | odd generation only |

Each slot is:

| Slot offset | Size | Field |
|---:|---:|---|
| 0 | 1 | generation |
| 1 | 1 | stage |
| 2 | 1 | outcome: progress=`0`, success=`1`, failure=`2` |
| 3 | 1 | item index |
| 4 | 2 | detail/errno magnitude, bounded to `0..4095` |
| 6 | 4 | CRC32 commit word |

The slot CRC covers a fixed domain string, the complete 25-byte shared header,
the slot ID, and the six-byte slot body. CRC zero is reserved for an
uncommitted slot. A valid generation must have parity equal to its slot ID.
Every valid non-entry generation must equal the ordinal of its stage in the
selected profile.

The shared header needs no separate checksum because every valid slot CRC
covers it. A header change invalidates both slots. The 128-bit run ID remains
the short in-record binding; full Image, boot, AP, manifest, patch, and checker
SHA256 identities remain outside the record in the immutable candidate and
Process v2 closure.

Before accepting a future run ID, the static checker must encode every
reachable E1A/E1B slot and the UNSAT form. It rejects any record containing a
second evidence-family occurrence and any reachable slot whose computed CRC32
is zero. These are candidate-selection constraints, not runtime retry cases.

## Short UNSAT Record

Keep the proven threshold partition:

```text
S22E1U1| [8-byte family] + candidate-derived 16-byte tag = 24 bytes
```

The tag is domain-separated from the long record and derived from the exact
profile/run contract. It is diagnostic only and never arms the proc writer.

| Valid retained state at post-exec hook | Action |
|---|---|
| valid magic and `idx >= 45` | place the 45-byte ENTRY A/B record |
| valid magic and `24 <= idx < 45` | place the 24-byte UNSAT record |
| invalid magic or `idx < 24` | write nothing |

Wrong target, path, PID, DT layout, reserved range, or physical mapping also
writes nothing. No branch changes `magic`, `idx`, `prev_idx`, or `boot_cnt`.

## Request ABI

Userspace retains a fixed 32-byte request shape:

```text
<4s magic="S22Q", u8 version=2, u8 profile, u8 stage, u8 outcome,
 u16 detail, u8 item, u8 reserved=0, u8 run_id[16], u32 crc32>
```

The request CRC covers its first 28 bytes. The kernel accepts only PID 1, exact
length and offset, version 2, the compiled profile/run ID, a valid CRC, the
exact successor stage, the stage-specific item index, and these outcome rules:

- progress: nonterminal stage and zero detail;
- failure: nonterminal expected stage and nonzero detail;
- success: exact profile terminal and zero detail;
- after failure or success: no further request.

## Profiles

E1A deliberately repeats the already evidenced procfs checkpoint. A terminal
record must prove the complete current candidate path, not inherit a previous
candidate's live result.

E1A sequence:

```text
ENTRY
PROC_MOUNTED -> SYS_MOUNTED -> DEV_TMPFS_MOUNTED -> RUN_TMPFS_MOUNTED
-> DEV_NODES_VERIFIED
-> CHILD_EXEC_STARTED -> CHILD_TOKEN_VERIFIED -> CHILD_REAPED
-> E1A_SUCCESS
```

E1B repeats E1A's operational stages, then continues without publishing the
E1A terminal:

```text
... -> CHILD_REAPED
-> WDT_MODULE_0 -> WDT_MODULE_1 -> WDT_MODULE_2
-> WDT_MODULE_3 -> WDT_MODULE_4 -> WDT_MODULES_VERIFIED
-> E1B_SUCCESS
```

Module stages require item indices `0..4`; every other stage requires zero.
E1B success proves the repeated local runtime plus the watchdog closure in one
boot. It does not prove platform bind, UDC, or USB.

## A/B Update Protocol

The post-exec hook initializes the shared header, committed generation-zero
ENTRY in slot A, and an uncommitted slot B. It arms the proc writer only after
exact readback, cache flush, and an unchanged Samsung header.

For each accepted userspace request:

1. reopen and validate the retained header against frozen `magic`, `idx`, and
   `boot_cnt`;
2. select the inactive slot and clear its four-byte commit CRC;
3. flush that invalidation and issue the required barrier;
4. write the six-byte body, flush, and recheck the retained header;
5. write the nonzero CRC32 commit word last and flush it;
6. read back the complete slot and recheck the retained header;
7. only then advance the in-memory generation and return success.

If reset or failure occurs before step 5 completes, the other slot remains the
prior valid generation. A nonzero slot with bad CRC or invalid semantics is
invalid by itself and does not discard the other valid slot. Two valid slots
must be adjacent generations, and the older one must be progress. No valid
slot means no proof.

A valid newly committed slot proves that the kernel stored that request. As in
P2.31, it does not by itself prove the write syscall returned to userspace if a
post-store header check later failed.

`seed_idx` and `boot_cnt` remain frozen kernel state rather than record fields.
The compact observer therefore does not infer exact boot chronology from a
record. It only reports the count of independently valid retained records as a
lower bound on evidenced candidate boots.

## Observer And Multiboot Policy

Connected D0 must collect a complete baseline that contains no P2.32 long or
UNSAT family, no P2.19 legacy family, and no recognizable family fragment at
either snapshot edge.

After rollback, the decoder scans raw bytes and requires:

- every `S22E1L1|` occurrence to contain one complete 45-byte record;
- the exact expected profile and 128-bit run ID;
- at least one valid A/B slot per record;
- valid slot parity, generation, stage, outcome, item, detail, and CRC;
- every `S22E1U1|` occurrence to equal the candidate-specific 24-byte record;
- no legacy, foreign, malformed, or edge-partial family.

Acceptance is existential and explicit: one or more records whose active slot
is the declared E1A or E1B terminal success proves that at least one candidate
boot completed that rung. Other fully valid ENTRY, progress, failure, or UNSAT
records from recovery reboots remain reported diagnostics and do not erase a
valid success. Any malformed or foreign record makes the whole observation
fail closed. This proves capability, not repeated-boot reliability; a soak or
reliability claim needs a separate policy.

Without a terminal success, the highest valid stages and first failure errno
are diagnostic only. Zero remains `ZERO_AMBIGUOUS` and supports no positive
inference.

## Executable Contract

The pure host model fixes the byte layout, request encoding, strict successor
rules, A/B fallback, terminal semantics, multiboot policy, and 24/45-byte
visibility boundaries:

`workspace/public/src/scripts/revalidation/s22plus_fyg8_p232_e1_latest_stage_design.py`

Focused tests cover request tampering, skip/replay/wrong identity, profile
completion, slot parity, torn invalidation/body, CRC-valid semantic corruption,
terminal failure, dirty baseline, legacy/foreign/malformed/partial records,
multiboot recovery states, and invalid-magic/nonselection controls:

`tests/test_s22plus_fyg8_p232_e1_latest_stage_design.py`

## P2.33 Implemented Closure

P2.33 implements and statically validates only:

1. one P2.25-derived guarded kernel patch with exact 45/24-byte layouts,
   compact A/B writes, cache flushes, and header checks;
2. version-2 E1A/E1B checkpoint client and the two bounded runtime profiles;
3. one opt-in raw decoder/evidence kind using the fixed multiboot rule;
4. static control-flow checks that terminal publication is dominated by every
   required operation, that `sec_log_buf.ko` is absent, and that the selected
   run ID passes the family-collision and all-reachable-CRC checks; and
5. focused adversarial tests plus one independent review of that changed
   execution-critical closure.

The implementation passes as
`PASS_P233_E1_SOURCE_IMPLEMENTATION_HOST_ONLY`. The typed adapter deliberately
rejects offline promotion until a future candidate-bound contract exists.
P2.33 remains H0: it built no kernel or image, created no ready manifest,
contacted no device, invoked no Odin, and authorized no F1. Clean build,
artifact closure, D0, approval, and live execution remain separate units.

`docs/reports/S22PLUS_FYG8_P233_E1_SOURCE_IMPLEMENTATION_HOST_PASS_2026-07-22.md`
