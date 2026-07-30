# S22+ FYG8 P2.90 checked-park and adjacent-corridor H0

Date: 2026-07-31
Risk tier: H0 only
Device authority: none
Predecessor: closed P2.88 run `20bb4d70842fe7ae1a6bd0aec261d722`

## Result

`PASS_P290_CHECKED_PARK_ADJACENT_CORRIDOR_IMPLEMENTATION_HOST_ONLY`

P2.88 did not establish that generation 89 was attempted. Its first new
position was on the far side of the unobserved generation-88 publisher-return
boundary, and fourteen inherited park routes could still end with an unchecked
or non-returning publication. P2.90 fixes the host-side contract defect before
another live attempt:

- the first successor position is `(stage=0x8f,item_index=1)` immediately after
  the accepted generation-88 publisher returns;
- three more `(0x8f,item_index=2..4)` positions cover suspend return, restart
  entry, and deadline completion before the inherited `(0x90,0)` helper
  dispatch;
- all generic park routes check the unclassified fallback result;
- exact failure publishers check the primary result, then check a reserved
  unclassified fallback;
- a raw park is reachable only through one confirmed-publication sink or one
  explicitly named persistent checkpoint-channel-failure sink; and
- the retained ABI remains one 45-byte record with two alternating slots.

No regulator sysfs predicate, new module, device operation, or F1 machinery was
added. The purpose of P2.90 is attribution under failure, not a new USB repair.

## Corrected predecessor facts

The materialized P2.88 candidate has twelve bind gates. The earlier count of
eight came from the historical P2.41 header and is not the candidate value.
Gate failure still calls `fail_at()` and is therefore not, by itself, a silent
park explanation.

The P2.88 production validator proof is exact:

- active generation domain: `0..103`;
- stage/item domain: `256 * 256`;
- checked requests: `6,815,744`;
- accepted requests: `103`, exactly one for each generation `0..102`; and
- terminal generation 103 accepts no successor.

That proof establishes validator semantics for a supplied request. A separate
P2.90 source gate establishes the runtime request construction:

1. `S22_P290_POSITION_RESTART_HELPER_DISPATCH` is ordinal 92;
2. the runtime calls `p290_progress_position(..., 0U)` exactly once;
3. the client requires the supplied ordinal to equal
   `client->generation`;
4. it copies stage and item from linked step 92; and
5. linked step 92 is exactly `(0x90,0)`.

## Retained-slot implication

The two preserved P2.88 reads are byte-identical. The active slots are:

- slot 1: generation 87, stage `0x8e`, item 0, detail 0;
- slot 0: generation 88, stage `0x8f`, item 0, detail `0xc18`.

The writer uses `next_slot = active_slot ^ 1` and writes directly to the target
slot in this persistent order:

1. clear target `commit_crc`;
2. flush;
3. write target body;
4. flush;
5. write target commit CRC;
6. flush;
7. verify;
8. update only the userspace client's local generation.

There is no separate persistent staging slot. Generation 89 therefore targets
slot 1. Because the old generation-87 slot remains fully valid, generation 89
did not reach even the target-slot CRC clear. A generation-89
post-commit/state-advance `-ESTALE` path cannot explain this retained image.
A generation-88 post-commit error remains nested inside the broader class
"generation-88 primary publication error followed by fallback failure or
non-return."

## Park-route repair

The historical P2.86 include contains sixteen `quiet_park()` sites. P2.90
mechanically accounts for all sixteen:

- twelve surviving historical sites route through a checked unclassified
  fallback;
- two sites are already reached only after a confirmed durable publication;
- two sites were removed and made unreachable by the inherited P2.88
  transformations.

After successor substitutions, the materialized P2.90 include contains
fourteen generic checked-fallback calls and three
confirmed-publication calls. The wrapper contains exactly two raw park calls:
one in `p290_park_after_confirmed_publication()` and one in
`p290_checkpoint_channel_failure_sink()`.

The final sink is deliberately not described as self-reporting. The retained
checkpoint is the sole persistent channel, so it cannot durably describe its
own total failure. Its exact residual class is:

- a primary or fallback publication never returns; or
- primary and fallback both return errors.

This is the irreducible one-channel limitation. P2.90 reduces fourteen
anonymous attempt-only routes to this one defined class without claiming an
impossible final marker.

## Adjacent corridor

The live-proven prefix through generation 88 is byte-for-byte inherited.
P2.90 inserts:

| Generation | Pair | Meaning |
|---:|---:|---|
| 89 | `0x8f/1` | generation-88 publisher returned |
| 90 | `0x8f/2` | suspend function returned to caller |
| 91 | `0x8f/3` | restart function entered |
| 92 | `0x8f/4` | restart deadline creation returned |
| 93 | `0x90/0` | peripheral helper dispatch |

The generation-89 call is immediately after
`p282_publish_classification()` and before `p282_cycle_suspend()` returns.
There is no gate revalidation, unrelated syscall, tracefs read, or helper call
between the two publishers. Runtime call order is derived and checked against
the declared position sequence; removal, displacement, unchecked fallback, or
raw-park escape mutations fail closed.

The full sequence is 107 unique `(stage,item_index)` pairs. Terminal generation
is 107, so the `u8` generation cannot wrap and any post-terminal publication is
rejected.

## Identity partition

P2.90 inherits all 83 frozen P2.88 receipts unchanged and adds:

- eight direct byte-affecting sources; and
- three generated byte-affecting sources.

The resulting identity has exactly 94 `SOURCE_KEYS`: 82 direct and 12
generated. Candidate intent, userspace build, kernel build, candidate builder,
and boot-only packager are inside identity. Decoder, selector, candidate
contract, linked/static/freeze validators, evidence glue, tests, and this
report remain outside identity and must be approval-bundle-bound.

The frozen P2.88 intent was reopened from private storage and all `83/83`
receipts match with `CHANGED_KEYS=[]`.

## Host validation

The focused contract and predesign suites prove:

- the 107-pair sequence and unchanged generation-88 prefix;
- exact runtime construction of helper dispatch `(0x90,0)`;
- all historical park sites accounted and all active generic fallback returns
  checked;
- primary-success, primary-error/fallback-success, double-error, legacy, and
  non-return fault paths;
- the single residual persistent-channel failure class;
- exact first-marker adjacency and mechanical runtime publication order;
- deterministic generation and clean kernel-patch application;
- two byte-identical static AArch64 userspace links;
- no P2.88 position header or macro left in generated P2.90 C;
- direct ELF symbol-data equality for the linked stage, item, kind, and detail
  tables; and
- a register-allocation-independent exhaustive validator run over
  `108 * 65,536 = 7,077,888` inputs with exactly 107 accepts.

The exhaustive mutation test reverses the production item comparison and is
rejected. The park mutation tests remove a position, insert a syscall into the
adjacency, invert the fallback check, and add a raw park; every mutation is
rejected.

## Safety and next boundary

This report is host-only. No device was contacted, no image was built, no
candidate was packaged, no intent was derived, and no F1 is authorized.

Before an intent is derived, the Git-derived change window must exactly equal
the declared payload/support/governance set and print all 94 source keys with
zero inherited receipt changes. After intent, none of those 94 keys may
change. Full-LTO A must pass the private/clang-path leak gate before B starts.
Only a byte-identical A/B pair plus formal linked/static/package closure may
advance to a future ready manifest and fresh D0/F1 review.
