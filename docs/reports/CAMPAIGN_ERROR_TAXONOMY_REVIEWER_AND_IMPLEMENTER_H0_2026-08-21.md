# Campaign error taxonomy: reviewer and implementer, kept separate

Host-only. Non-binding. This document grants no D0, D1, or F1 authority and
changes no contract. `AGENTS.md` and the selected target contract remain the only
binding layers.

Two agents produce work in this repository: an implementer (Codex/Luna MAX, which
writes runners, auditors and candidate machinery) and a reviewer (Claude, which
attacks that work and records findings). Their errors are **not** the same kind of
error, they are not caught by the same gate, and mixing them into one "mistakes"
list is why neither has been reduced.

They are separated here on purpose. The comparison at the end is the reason the
separation is worth the space.

## Method

Mined, not recalled. Sources: the reviewer's own running tally
(`feedback-claim-calibration`, 40 KB, maintained since 2026-08 across eight review
sessions), the 51 report sections pinned in
`tests/test_s22plus_fyg8_p319_stock_choreography_docs.py::SECTION_ORDER`,
`docs/operations/CAMPAIGN_LEDGER_S22PLUS.md` (331 dated rows), and the 54
incident/postmortem reports under `docs/reports/`.

Corpus scale as of 2026-08-21: 5,481 commits since 2025-11-13, 2,463 reports,
1,333 test files, 543 ledger rows across two campaigns.

Only defects that were **confirmed at source and acted on** are listed. Objections
that were raised and dropped are recorded as such, because a dropped objection is
data too.

---

# Part 1 — Reviewer errors (Claude)

## R1. Narrow sample generalised to the whole medium

The dominant shape. Seven confirmed instances, most caught by someone else.

| # | Sampled | Concluded about | Reality |
|---|---|---|---|
| 1 | one bootloader log format (159 lines) | the whole log | 1,168 more lines in a second format, 297 MUIC |
| 2 | one evidence channel (`candidate-observer.raw`) | all channels | the Carrier delivers frames on another |
| 3 | the runtime transform scripts | the candidate | population is `materialized-sources`; 79/163, not 107/108 |
| 4 | one branch of a function | the function | the other branches contradicted it |
| 5 | two log formats | the log | a third (`[ ABL ]`) existed |
| 6 | `max77705.h` | "no BCCTRL1 bitfield exists" | it is in `max77705-muic.h:233-246` |
| 7 | an immediate-operand search | "GCTL is never written" | two sites existed |

**Structural cause.** Prose has no type checker. A sentence can quantify over a
population the author never enumerated, and nothing stops it being written.

**Countermeasure that works.** Name the population *before* the count, and prove
enumeration over it. The campaign built the right instrument for this:
`tests/test_s22plus_fyg8_p319_evidence_crosscheck.py` **recomputes** each number
from evidence instead of pinning the report's wording. Three deliberate
corruptions produced exactly three failures. Prose-pinning tests stay green while
the prose is wrong — that is how instance 3 reached publication.

## R2. Answering from recollection when the artifact is in the tree

**Confirmed 2026-08-21.** Asserted that a rebuilt vendor module "must reproduce
the shipped vermagic exactly", and built a sequencing recommendation on it. The
loader does not compare that token:

```c
/* First part is kernel version, which we ignore if module has crcs. */
if (has_crcs) { amagic += strcspn(amagic, " "); bmagic += strcspn(bmagic, " "); }
```

`common/kernel/module.c:1395-1404` — materialized in this repository, present the
whole session, never opened.

This is the same family as the older rule "call paths and inlining must come from
the candidate `vmlinux`, not the `.c`", one level up: **semantics of a mechanism
are an artifact, not a memory.** The observation underneath (two vermagic strings
exist on this host) was true. The conclusion drawn from it was invented.

## R3. Stale reassertion of a withdrawn claim

A claim was withdrawn in one section while three other sections continued to
assert it. Found by sweeping for the claim's tokens, not by reading.

**Countermeasure, now standard.** A withdrawal is only real when it is **pinned**
— a test asserts the withdrawal token is present *and* the withdrawn phrasing is
absent, so the old claim cannot silently return. This is unusual practice and it
is correct; keep it.

## R4. Doing the thing being argued against

While writing a section arguing against capture-specific constants, hardcoded
`irq:350` into the token list of that same section. Caught by the implementer.

## R5. Accounting errors in the reviewer's own bookkeeping

- Ledger identifier collision, **twice** — quoted an ordinal space-delimited in
  prose, tripping the test that parses ordinals out of the ledger. The second
  instance was in the row written to *correct* the first.
- Review rows that discharged nothing: used a plain `P319_…` action and put
  "review" inside the topic segment, so the rows registered as **new pending
  obligations** and the total went up. The operator caught it.

**Structural cause.** The ledger grammar is machine-enforced but the reviewer
writes prose in the same field. Not a knowledge failure; an interface failure.

## R6. Committing while the suite was red

The commit gate was `grep -E "^(Ran|OK|FAILED)"`, which **matches** `FAILED`.
Fixed to gate on the failure *count* (`grep -cE '^FAIL:|^ERROR:'`).

A gate that pattern-matches an outcome word instead of counting failures is not a
gate. This is a specific instance of R7.

## R7. Proposing something that does not satisfy the constraint it is named after

Proposed a "read-only D0" observation that required a reboot (explicitly excluded
from D0) and raw I2C (not a sysfs/procfs read). Worse, the observation was
impossible in principle: the code path that would have been read runs on the
rollback boot too, erasing the evidence.

**Countermeasure.** Before naming a tier, quote the tier's own text and check the
proposal against each clause.

## R8. Post-compaction staleness

An A90 session after a context compaction produced **four claims, four rejected**.
The reviewer reasoned from a summary rather than from the tree.

**Countermeasure.** After compaction, re-read the authoritative artifact before
issuing any claim about it. Treat the summary as an index, never as evidence.

## R9. Operational self-inflicted noise

Ran the full S22+ suite in the background while running the P3.19 suite in the
foreground over a shared private output root, producing **124 phantom
failures/errors**, and read them as real for one turn. The modules pass 24/24
alone.

---

# Part 2 — Implementer errors (Codex / Luna MAX)

The implementer's work is, by volume and by quality, very good: large auditors
that fail closed, exact byte pinning, no-clobber receipts, deterministic
regeneration. The defects are therefore **not** sloppiness. They are systematic,
and they cluster in three places.

## I1. Binding the wrong input

The machinery is correct and it is pointed at the wrong artifact.

- **Wrong-run build authority (2026-08-21, confirmed, repaired).** The auditor
  pinned the flashed Image `71f573eb` but took its section authority, symbol CRCs
  and `.config` from `p310/immutable-a-v6`, whose own Image differs from the
  flashed one in **565 of 633 64 KiB blocks, 19.65% of bytes**. The auditor's own
  `RUN_ID = b9cc424d…` contradicted the run identity inside the config it used as
  authority (`a06fa64d…`).
- **Manifest SHA coupling.** Authority bound to a manifest hash that changed when
  only duplicate paths changed, so audits broke on semantically identical input.
- **Emitters not in the plan.** The transport binding named emitters that the
  effective module plan did not contain.

**Structural cause.** Adjacency is mistaken for identity. A sibling directory
holding a file with the right *name* is treated as the matching artifact. Nothing
in the tree records which build produced which output.

## I2. Freezing a derived value as a pass constant

A number that should be recomputed is pinned as a literal, and the pin then reads
as evidence.

- **`31/28` value-field differences**, described as "the expected differences".
  They were not a format quirk; they were the signature of a different link. The
  constant absorbed the defect and made the audit pass over it.
- **EUD index literal `37`** where the plan derived `38`.
- **`IMAGE_SECTION_LAYOUT`** — five bare offset literals, still inherited from the
  removed authority (`35,693,760 = 0x221A4C0 - 0x10000`), where the five sections
  are in fact exactly contiguous and four of five are derivable.

**Structural cause.** The same process writes the code and the test that admits
it. A constant makes both pass. There is no adversary inside the unit.

The campaign has already stated the correct rule once — *"17·16/1·111 are not pass
constants, they are recomputed results"* — and then re-introduced the shape twice.
It needs to be a mechanical check, not a slogan.

## I3. Proving a weaker proposition than the one claimed

The proof is valid; the headline is broader than the proof.

- **`S7A2` proves a correct module plan**, not that any module loaded, bound, or
  probed successfully. Self-corrected after review.
- **`probing Complete` is not a receipt** for MUIC initialisation or for a
  successful bit-3 unmask.
- **Closure inflated by unused paths** — the count included paths that no
  consumer reached.
- **The 73-row materialization** was described as 14 increments; the real
  increment was 3.

**Structural cause.** The unit's report is written by the party that wants it to
close.

## I4. Fail-open under a fail-closed banner

Found by Luna MAX inside the implementer's own Envelope-v5 work: a **MUX
fail-open**, plus a string-parity defect and a default receipt-path defect. An
audit that is fail-closed everywhere except one branch is fail-open.

## I5. Shared mutable state under strict audits — *the same incident as R9*

`_strict_directory()` requires an exact child set over a **fixed** private output
root. Correct as a check; fatal under concurrency, and a Codex loop runs in
parallel in this repository. The check is right; the shared directory is wrong.

**This is not independent evidence.** Its single instance is the reviewer's own
concurrent-suite run recorded at R9, entered on both sides of the ledger as
though it were two patterns. One incident with two contributing causes is a fair
blameless reading; presenting it as an implementer pattern with n=1 is not.
Counted once, I5 is a design observation, not a demonstrated error class.

## I6. Schema drift in the ledger

Of the dated rows in the `## Log` section, **4** carry 8 fields where the schema
is 9; every other row conforms. Small, but it is the ledger, and the ledger is
the accounting authority.

An earlier version of this line also reported "one dated prose line" as a
malformed row. That was **a defect in this document's own guard**, not in the
ledger — see Part 4, M-4.

---

# Part 3 — The comparison, which is the point

| | Reviewer | Implementer |
|---|---|---|
| Error is about | **what is true** | **what is bound / what was proven** |
| Typical form | a sentence quantifying over a population never enumerated | a correct proof, pointed at the wrong input or labelled too broadly |
| Caught by | someone else reading it; almost never by tests | almost never by its own tests, because its tests are written with it |
| Cost when missed | a wrong direction, hours to days | a candidate qualified on the wrong basis — potentially a device action |
| Fix class | enumerate the population; open the artifact | derive the constant; bind by identity, not adjacency |

## The finding this taxonomy exists to state

Sorting the reviewer's tally by outcome produces a sharp split:

- **Findings about *binding* and *proposition* are almost always accepted.**
  The wrong-run authority, the manifest coupling, the emitters missing from the
  plan, the inflated closure, the review-row-is-not-a-resolution, the rebuild
  cost, `37` vs derived `38`.
- **Findings about *mechanism* were rejected across the P3.19 arc.**
  The DWC3 module-collapse framing, the exact-vermagic requirement, most of the
  P3.13 mechanism details, all four post-compaction A90 claims.

> **Weakened 2026-08-21 after independent rebuttal.** The second bullet
> originally read "*Findings about mechanism are usually rejected*", and the
> reviewer's own record refutes that as a general law. See Part 4, M-1.

This is not a coincidence and it is not about relative competence. The implementer
reads the mechanism more carefully than the reviewer does, because it has to make
the mechanism run. What it cannot check is whether the thing it bound is the thing
it meant, or whether the sentence in the report is the sentence the code proved —
because it is the same party doing both.

**Therefore: the reviewer should attack the binding and the proposition, and
should not attack the mechanism without opening the artifact first.** The second
half survives the rebuttal in Part 4 and is the operative rule; the first half is
a description of one arc, not a prediction. The original text claimed it
"predicts where the next accepted finding will come from" — **that claim is
withdrawn.**

## What each side should build next

**Reviewer.** Before issuing any claim about a mechanism, open the materialized
artifact and quote it. Before any count, name the population. After compaction,
re-read before speaking. These are cheap and all three failures above were free to
avoid.

**Implementer.** Two mechanical checks, both small:

1. **Every output directory gets a provenance record** — the config hash, the run
   id, and the exact inputs that produced it. `I1` becomes impossible to express.
2. **Every pinned numeric constant gets a derivation function or a written reason
   it is irreducible.** `I2` becomes visible at review time instead of at
   qualification time.

See `docs/operations/CAMPAIGN_METHODOLOGY_H0_2026-08-21.md` for the method
inventory and the external practices these two checks come from.

---

# Part 4 — What this taxonomy missed, found by rebutting it

Parts 1 through 3 were written by the reviewer, including the part that
classifies the implementer. That is the same self-review shape the document
criticises, so the documents were handed to a third model — GPT-5.6 Sol, served
as Daybreak Blue — with the instruction to rebut rather than judge, read-only,
with repository access.

It is a party to the dispute, not an arbiter: it is the same model family that
produces the implementer's work. Its factual recomputations were checked here at
source and are reported as verified; its opinions about its own error categories
are recorded as what they are.

## M-1. The central claim was overstated, and the reviewer's own record refutes it

The tally underneath Part 3 has **seven rows covering eight review sessions: 70
claims issued, 35 accepted, 3 accepted with correction, 30 rejected or
self-dropped, 2 open**. Recomputed and confirmed. It has **no
binding / proposition / mechanism column at all** — that classification was
applied afterwards, by the same party the tally is about, outside the artifact.

And the record carries direct counterexamples. On 2026-08-10, the findings that
**survived** were:

- `dwc3_resume_common` discards `dwc3_gadget_resume`'s return, so a gadget-resume
  failure is invisible to userspace;
- the plan dropped the parent-suspended wait the existing cycle already performs;
- no record budget against `P282_RECORD_CAPACITY 64`, where overflow is
  fail-closed `-EOVERFLOW`.

All three are **mechanism** findings. All three were accepted.

So "mechanism findings are usually rejected" was a generalisation from the P3.19
arc to the whole record — **the narrow-sample-to-whole-medium shape catalogued as
R1, committed inside the document that catalogues it.** Fifth instance in one
session.

What survives is narrower and still useful: *in this arc, the reviewer's
mechanism claims were wrong when the reviewer had not opened the artifact.* That
is R2 restated. It is not a law about claim types, and it predicts nothing.

## M-2. A third error class exists that neither Part 1 nor Part 2 has

**Unrecorded exogenous-state drift**: operator, host, or physical state that
neither the reviewer nor the implementer controls, and that no artifact records.

The instance is P3.17. The candidate enumerated high-speed at `3-1.3` under
`0000:00:14.0` and bound `cdc_acm`
(`docs/reports/S22PLUS_FYG8_P317_HISTORICAL_ENDPOINT_REPLAY_RECOVERY_INCIDENT_2026-08-14.md:197`)
— a different controller from the one the observer was pinned to. The observer
was correctly pinned. The implementer's code was correct. The reviewer had
nothing to catch. **The world moved and nothing in the tree recorded that it
had.**

This class is invisible from inside a two-party setup because both parties are
looking at artifacts, and the defining property of this class is that no artifact
exists. It is the strongest argument in the document for X1: a provenance record
is the cheapest way to make an unrecorded input *become* an artifact.

## M-3. "This repository has no hooks" was wrong

Stated by the reviewer while proposing an enforcement split. The repository sets
`core.hooksPath = .githooks` and `.githooks/pre-push` exists and is executable.
It blocks on identifier-boundary failure — a device serial reaching a remote —
and it says in its own header that it cannot determine whether review happened.

The reviewer checked `.claude/settings.json`, found no hooks there, and concluded
about hooks in general. **R1 again, sixth instance in one session**, and this one
was found by a party that simply ran `git config --get core.hooksPath`.

The corrected position: one hook exists, it would have prevented none of R1–R9,
and of the nine only **R6** is directly preventable by a commit gate reading a
real test exit status. R9 is preventable by a lock, because two processes sharing
a directory is observable state. R1, R2, R7 and R8 are semantic and outside any
hook's reach.

## M-4. Two guard defects in this document's own tests

- The ledger guard scanned every date-prefixed line in the whole file, so a
  narrative sentence beginning with a timestamp was counted as a malformed row.
  The "one dated prose line" figure was a guard artifact, not a ledger defect.
  Fixed: the guard now scans only the `## Log` section.
- The method section described `SECTION_ORDER` as "51 review sections". It is 51
  **report** sections, of which 5 are titled "Review of…". Corrected.

## What the rebuttal got wrong

Recorded so the rebuttal is not treated as more authoritative than it is.

- It called **17 of 24 methods form-without-substance**, grouping M4, M5 and M6
  under one incident. M5, exact-byte identity, is the mechanism that *detected*
  the provenance defect. The charge is too broad for its evidence.
- On **I2** it argued `IMAGE_SECTION_LAYOUT` is not an error because the review
  called it correct and non-blocking. The review said the value is correct and
  **not derived**; those are different claims.
- It classified **R9** as a semantic error outside hook reach. Two processes
  writing one directory is exactly the kind of state a lock observes.

## What this changes

The implementer's two mechanical checks in Part 3 stand unchanged; the rebuttal
did not touch them. What changes is the reviewer's side: one law becomes one
habit, one error class is added that belongs to neither party, and the count of
R1 instances in a single session goes from five to six.
