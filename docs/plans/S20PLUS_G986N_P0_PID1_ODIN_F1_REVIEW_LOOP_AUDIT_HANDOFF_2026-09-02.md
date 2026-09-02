# S20+ P0 PID1 Odin F1 review-loop audit handoff — H0

Date: 2026-09-02
Target: Samsung Galaxy S20+ 5G `SM-G986N` / `y2q` / `G986NKSS8IYC2` only
Tier: H0 process audit
Device contact: none
Authority: none — this handoff allocates no candidate, approval, ordinal,
journal, D0, D1, F1, P0, transfer, reboot, rollback, or replay, and it does not
retire, weaken, or supersede any finding from any prior independent review

Sources read: `docs/reports/S20PLUS_G986N_P0_PID1_ODIN_F1_OWNER_H0_2026-09-01.md`
(committed and working-tree states), `GOAL_S20PLUS.md`, `AGENTS.md`,
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`. No code was executed
and no file under review was modified.

## Decision requested

Decide whether the **next** P0 qualification gate runs under the same process
as the previous ones, or under a bounded process with an explicit stopping
rule.

This is not a request to lower the review bar on a path that writes a
partition. It is a request to decide where that bar is pointed.

## Why this is being asked now

P0 has passed through **fourteen** gates. Three returned `PASS_GO` at `0/0/0`.
Zero resulted in activation. The current state, after the working-tree
correction of 2026-09-02, is:

- report status `PASS_GO_ACTIVE_ATTENDED_F1` → `H0_REVIEW_PENDING_NOT_ACTIVE`
- goal status `P0_PID1_ODIN_F1_ACTIVE_ATTENDED` → `P0_PID1_ODIN_F1_REVIEW_PENDING_NOT_ACTIVE`
- `AGENTS.md` registry row: `reviewed attended native-canary P0 F1 active` removed

A process where a `PASS_GO` does not discharge an obligation is not converging.

## The gates

| # | Result | What stopped it |
|---|---|---|
| 1 | `NO_GO` 2/4/2 | directly callable dormant effect helpers; inherited B0 positives; non-raw ACM evidence |
| 2 | `NO_GO` 2/2/2 | ungated inherited low-level calls; no target-session lease; unjournaled cage cut |
| 3 | `NO_GO` 4/3/0 | forgeable caller-created lease boolean; global claim before transfer preflight |
| 4 | `NO_GO` 4/4/0 | sentinels/ContextVars module-accessible; raw and journal primitives directly callable |
| 5 | `NO_GO` 1/2/0 | free-substring activation markers; raw writer FDs outliving the lease |
| 6 | `NO_GO` 5/0/0 | closure introspection; Markdown status placement; stale activation binding |
| 7 | **`PASS_GO` 0/0/0** | retired before activation — focused tests required the booleans to be false |
| 8 | `NO_GO` 1/3/2 | ADB caller redirection; dormant-only observer pinning; ambient negative-test state |
| 9 | `NO_GO` 1/0/0 | one owner test rewrote `OBSERVER_ACTIVE` and asserted dormant bytes |
| 10 | stop | loader pinned dormant 16,487 B; the reviewed `False`→`True` atom yields 16,486 B |
| 11 | `PASS_GO` 0/0/0 → 59/60 | document-normalization test assumed the repository was dormant |
| 12 | stop | expired TWRP-owner test demanded a target-contract error under active atoms |
| 13 | stop | `--prepare` blocked by the P0 registry writer fence it had installed |
| 14 | stop | private ADB server could not enumerate the device (see below) |

Gates 1–4 are excluded from every criticism in this document. They found real
defects in a module that will write a boot partition, and each correction
measurably narrowed the callable surface. That work should not be undone.

## Finding 1 — the failure category left the experiment at gate 7

Gates 1–4 concern the **device-effect surface**: what can be called, by whom,
in what order, with what journal.

Gates 7 and after concern the **activation bookkeeping**: whether the
repository can flip six status atoms without its own test closure contradicting
itself.

Not one gate from 7 to 13 concerned whether the S20+ candidate boots, whether
PID 1 arrives, whether rollback is available, or whether the device returns
healthy. Those are the questions P0 exists to answer.

## Finding 2 — severity does not decrease

```
2/4/2 → 2/2/2 → 4/3/0 → 4/4/0 → 1/2/0 → 5/0/0 → 0/0/0 → 1/3/2 → 1/0/0
                  ↑ top bucket rose after correction   ↑ rose again
```

A converging remediation trends the top bucket down. This one does not.

## Finding 3 — scope is not bounded

Gate 6 rested on a premise the repository itself rejects:

> The repository threat model explicitly excludes a malicious same-UID owner who
> reflects into Python closure cells or replaces the repository/runtime between
> individual calls

The premise was declared out of model **and the round still produced a
rewrite** (closure-private proxies, per-attribute acquisition grants, Markdown
comment/fence stripping). If an out-of-model premise can generate mandatory
work, the review has no upper bound.

Precedent for bounding a gate already exists in this repository:
`docs/plans/A90_RTIC_PUBLIC_MPGEN_CANARY_HAZARD_REVIEW_HANDOFF_2026-08-23.md`
states that an unbounded demand "is not by itself a falsifiable gate."

## Finding 4 — the decisive case: gate 8's fix broke the device path

Gate 8 required narrowing ADB ownership. The correction introduced a
transaction-private pinned ADB server on an internally random localabstract
socket admitting only one executable and peer PID/UID/GID.

Two later connected preparations then stopped at `exact S20+ ADB inventory is
absent or ambiguous`. In the second, the ordinary server saw exact healthy
`SM_G986N/y2q`, but it already held both USB interfaces, so the private P0
server could not enumerate either.

Between its introduction and its refutation, that machinery passed at least one
full-closure `PASS_GO` at `0/0/0` and four further gates. **No review found
it. Real hardware did.** The 2026-09-02 correction removes the private ADB
daemon lifecycle entirely (−227 lines, +37) and returns to B0's fixed
`tcp:5037` client.

This is the load-bearing evidence. After gate 6, the loop was not filtering
defects out of the device path — it was inserting one.

## Root cause — activation is self-referential

Activation sequence step 3 requires:

> keeping the reviewed test bytes unchanged and rerunning them under the active
> atoms

The test bytes must not change, and those same tests read the repository's own
dormant/active state. The state being flipped is an input to the check that
gates the flip.

```
activation attempt → state the tests observe changes → tests fail
        ↑                                                  │
        └──── add another normalization layer ←────────────┘
```

Gates 7, 9, 11 and 12 are four instances of this single defect. Gate 10 is its
purest form: flipping `False` to `True` shortens the observer by one byte, and
the loader pinned the byte size.

Each remediation adds a normalization layer — normalized hash, dormant/active
size map, activation-normalized receipts, derive-both-forms tests — and each
layer creates one more place where dormant and active can disagree. The
complexity is not a design choice; it is the residue of answering
self-referential findings.

## Proportionality

P0 is one boot-only AP, mandatory resident rollback, retained TWRP recovery,
attended. S22+ ran that same tier twelve times (P3.15–P3.26) under
`docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`, whose F1 is likewise
boot-only with an ephemeral child and mandatory rollback.

The S20+ owner carries machinery S22+ does not require at the same tier. That
asymmetry is not justified by a difference in device risk. It should either be
justified explicitly in the contract or reduced.

## Proposed process changes

**P1 — freeze the scope before the next gate.** Write the threat model and
review checklist for P0 as a document, and state that findings outside it are
recorded but do not gate activation. Same-UID closure reflection and
runtime-replacement premises are already out of model; name them explicitly.

**P2 — break the self-reference. Preferred: allow a reviewed test diff.**
Accept a reviewed, byte-pinned test diff as one of the three activation
records, instead of requiring test bytes to be invariant across a state change
the tests observe. This removes gates 7, 9, 11 and 12 as a class. It weakens no
device-safety property: the tests are still pinned and still reviewed.

**P3 — alternative, larger: move activation state out of the test-visible
tree.** If the six atoms lived in one private mode-`0400` record rather than in
tracked source and Markdown, flipping them would perturb no test input, and
gate 10's one-byte problem would not exist. This is the cleaner cut but a
larger contract change; P2 is worth trying first.

**P4 — require a proportionality note for new machinery.** Any correction that
adds a new privileged mechanism (a daemon, a socket, a capability layer) should
state what device-safety property it protects and what it costs on the live
path. Gate 8's private ADB server would not have survived that question.

## What must not be weakened

- The gate 1–4 class of finding: reachable effect primitives, forgeable
  capabilities, claim/preflight ordering, journal completeness.
- Mandatory resident rollback, retained TWRP recovery, attendance, no replay,
  target isolation, and the permanent forbidden-partition list.
- The requirement for a fresh connected preparation, its exact returned
  approval, and attended observation before any device command.

The recommendation is to re-aim the review, not to shorten it.

## Limitations of this audit

- The gate history was read from a report authored by the party under review.
  Finding texts are the author's summaries, not reviewer originals, so the
  categorisation in Finding 1 may be skewed toward the author's framing.
- Three facts are independent of that framing and carry the argument:
  three `PASS_GO` with zero activations; the 16,487/16,486 pair; and the gate-8
  private ADB server refuted by hardware after passing review.
- `GOAL_S20PLUS.md` narrates eight rounds while the report records fourteen
  gates. That drift is itself worth correcting.
- No claim is made here about whether the current working-tree bytes are
  correct. They remain review-pending, as their own status line states.

## What this handoff grants

Nothing. It requests one process decision. Every existing activation
prerequisite — exact-byte `PASS_GO`, the mechanical activation review, the
three private records, a healthy rooted Android return, a fresh connected
preparation with its exact returned approval, and attendance — remains
required and unchanged.
