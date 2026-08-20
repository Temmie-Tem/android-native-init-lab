# Campaign methodology: what works, what to promote, what to import

Host-only. **Non-binding.** This document grants no D0, D1, or F1 authority,
overrides nothing, and changes no contract. `AGENTS.md` and the selected target
contract remain the only binding layers. Nothing here may be cited as permission.

Companion: `docs/reports/CAMPAIGN_ERROR_TAXONOMY_REVIEWER_AND_IMPLEMENTER_H0_2026-08-21.md`.

The campaign has invented a set of methods that are, in places, better than
standard industry practice — and applies them unevenly, because most were never
named. Naming them is most of the value of this document. The rest is a short list
of outside practices that map onto specific defects this repository has actually
produced.

---

## Part 1 — Methods this campaign already invented

Keep these. They are load-bearing and several are unusual.

### M1. Bounded-population census

State an inclusion criterion once, apply it mechanically, deduplicate by content
hash before counting, and record what could not be read.

`s22plus_fyg8_p319_abl_log_census.py` selects every regular file under
`workspace/private` of exactly 2,097,136 bytes — not by name, not by run —
deduplicates by SHA-256, and reports `unreadable_or_short_files` rather than
silently excluding them. It also distinguishes **file identity from boot
identity**: 103 files held 268 boot segments.

This exists because of the reviewer's dominant error (R1). It is the direct cure.

### M2. Recompute, do not pin the prose

`tests/test_s22plus_fyg8_p319_evidence_crosscheck.py` recomputes each number from
evidence and compares it to the report. Three deliberate corruptions produced
exactly three failures.

A test that asserts a string stays green while the string is wrong. This
distinction is the single most useful testing idea in the repository.

### M3. Pinned withdrawals

When a claim is withdrawn, a test asserts the withdrawal token is present **and**
the withdrawn phrasing is absent. A correction that is not pinned regresses; this
has been observed (R3).

Unusual practice. Not standard anywhere. Keep it.

### M4. Append-only ledger with a resolution grammar

Obligations open with an ordinal `h0-<topic>-<N>` and an action ending
`_REVIEW_PENDING`; they close only with a matching `h0-<topic>-review-<N>` whose
action starts `PASS_GO_`. The grammar is machine-checked, so the accounting cannot
be talked into balancing.

Of 331 dated S22+ rows, 326 carry the 9-field schema, 4 carry 8, and one is a
dated prose line.

### M5. Exact-byte identity on every input

Size **and** SHA-256 on each pinned artifact, checked before use. Combined with
no-clobber receipts at mode `0400` and link count one, and audit-only
byte-for-byte reproduction of the receipt.

### M6. Fail-closed audits

`AuditError` on any deviation; strict directory child sets; refusal rather than
warning. The default is *stop*, and that is correct for a campaign whose failure
mode is a bricked device.

### M7. Risk tiers with named forbidden primitives

`DEVICE_ACTION_RISK_TIERS.md` plus an absolute forbidden list in `AGENTS.md`.
Absolute prohibitions stated as primitives, not as intentions, so they cannot be
reasoned around.

### M8. Blameless, dense incident reports

54 of them in Markdown, plus independent-review JSON. They record mechanism, not
fault. This is already better than most industry practice.

---

## Part 2 — Used once, should be rules

These worked. They were ad hoc. Promote them.

### P1. Independent re-derivation before review (N-version)

Before reviewing a unit's headline numbers, derive them again with disjoint code.

Applied 2026-08-21: the flashed Image was decoded from scratch — own string-blob
localisation, own PREL32 walk, none of the auditor's constants — producing
`7,222 / 3,566 / 328 / 3,238`, matching exactly. That converts "their numbers look
right" into agreement between two decoders.

**Rule to adopt:** any number derived from a binary decode requires either a
second independent decoder or P2 before it can be cited as evidence.

### P2. Break the invariant on purpose

An invariant nobody has violated deliberately is an assumption.

Applied 2026-08-21: when `vmlinux.symvers` was removed, the open question was what
still validated the decode. Rotating the CRC table by **one entry** dropped CRC
agreement from **3,238 to 0** — proving the import closure is self-validating, and
stronger than the external check it replaced.

**Rule to adopt:** every audit states at least one mutation of its input that
*must* make it fail, and a test performs that mutation.

### P3. Derive, do not assert

Every pinned numeric constant carries either a derivation function or a written
reason it is irreducible.

Applied twice: `STOCK_SUFFIX` was replaced by a suffix read out of the Image; the
`.config` was replaced by the Image's own embedded `IKCFG_ST` payload. Still
outstanding: `IMAGE_SECTION_LAYOUT`'s five literals, four of which are derivable
because the five sections are exactly contiguous.

### P4. Review without anchoring

Form the derivation before reading the implementer's rationale. Reading the
rationale first makes its framing feel like the space of possibilities — which is
how "the expected 31/28 differences" survived one review pass unchallenged.

### P5. Record objections that did not bite

A checked-and-dropped objection costs one paragraph and saves the next reviewer
the same hours. Two were recorded on 2026-08-21 (merged GPL export namespace;
unmodelled symbol namespaces), both inert, both cheap to re-check if the inputs
change.

---

## Part 3 — Outside practice worth importing

Ordered by value for cost **here**, not in general. Each is tied to a defect this
repository actually produced.

### X1. Build provenance records — *highest value, lowest cost*

**Practice:** SLSA / in-toto style attestation. Every build output carries a small
record naming the exact inputs, config, toolchain and identity that produced it.

**Defect it kills:** I1, the wrong-run authority. Two P3.10 builds exist, differing
in 19.65% of bytes and in exactly two config lines. The auditor bound the flashed
Image and a sibling's `vmlinux`/`symvers`/`.config` because they sat in a
directory with the right name. A `provenance.json` in each output directory
carrying the config SHA-256 and `E1_RUN_ID_HEX` makes that mix-up **unexpressible**
rather than merely detectable.

**Cost:** one JSON per output directory, written at build time. No backfill needed
— start with new outputs.

### X2. Detection-channel accounting on incidents — *highest information yield*

**Practice:** every incident records **what caught it**: a host test, an
independent review, a device symptom, or nothing until it had already cost
something.

**Why here:** 54 incident reports exist and nobody can currently answer "does the
test suite or the review catch more, and which class of defect does each miss?"
That answer decides where the next hours of gate-building go. Right now the
allocation is by intuition.

**Cost:** one frontmatter field per new incident.

### X3. Mutation scoring for auditors

**Practice:** mutation testing (Mutmut, Cosmic Ray). Perturb the input or the code
and require the test to fail.

**Why here:** the implementer already does this manually — the 2026-08-21 unit
records "widened-latch, source-binding, output-reopen, checkpoint, packaging, and
hostile-mutation attacks". Automating it produces a **score** per auditor, which
turns "we attacked it" into "this auditor detects 43 of 47 mutations, here are the
4 it misses". P2 is the manual version of the same idea.

**Defect it kills:** I2, pass constants. A constant that absorbs a real difference
will survive a mutation that should have been detected, and the score says so.

### X4. Severe testing as the acceptance rule (Mayo)

**Practice:** a claim is supported by a test only if the test would **probably have
failed** had the claim been false.

**Why here:** this is the epistemic principle underneath X3, P2 and M2, and stating
it once gives reviewers a single question to ask of any receipt: *what would this
audit have done if the claim were false?* For "the expected 31/28 differences", the
answer was **nothing** — which is exactly why it hid a different kernel binary.

**Cost:** free. It is a question, not a system.

### X5. Strong inference (Platt, 1964)

**Practice:** before running an experiment, write the branching tree — each
possible outcome and which hypothesis it kills. Prefer experiments that
discriminate, not experiments that confirm.

**Why here:** the campaign refutes serially and does it well, but the discriminating
tree is usually implicit. The current witness order (module `finit_module` results
→ bind/probe → VBUSDET return → 5-byte status + classification → bit-3 readback)
is in fact ordered by discriminating power per cost, with the cheapest and most
decisive first. That was reached by argument; writing the tree makes it
reproducible for the next frontier.

### X6. A stopping rule for a degenerating programme (Lakatos)

**Practice:** when a research programme survives only by adding auxiliary
hypotheses and stops predicting new facts, the programme — not the hypothesis — is
the suspect.

**Why here:** the campaign already has this insight as
`feedback-check-the-frame` ("N in-frame refutations with an unchanged symptom =
stop and audit the setup"), but with no threshold, so it fires late. Give it a
number: **three consecutive in-frame refutations with an unchanged symptom
triggers a mandatory frame audit** — enumerate what the frame assumes, and check
each assumption against an artifact.

Instance cost of not having the threshold: the module-plan diff went unasked for a
month.

### X7. Calibration scoring (Brier / Tetlock)

**Practice:** attach an explicit confidence to each claim before the outcome is
known, then score.

**Why here:** the reviewer's running tally already counts issued / accepted /
rejected across eight sessions. Adding one number per claim converts it from a
tally into a calibration curve, which answers a question the tally cannot: *is the
reviewer's confidence informative, or uniform?* The taxonomy's central finding —
binding-and-proposition claims land, mechanism claims do not — was extracted by
hand and would fall out of a scored tally automatically.

**Cost:** one integer per claim.

### X8. Hermetic, content-addressed builds (Nix / Bazel)

**Practice:** outputs keyed by the hash of their inputs; a sibling directory's
artifact cannot be picked up by accident because paths are content-addressed.

**Why here:** the correct endpoint for X1. **Do not do this now** — the migration
cost is very large against a campaign mid-frontier, and X1 captures most of the
benefit for a fraction of the cost. Recorded so the cheap fix is understood as an
approximation of a known good design, not as a workaround.

### X9. Property-based testing (Hypothesis) — *honest downgrade*

Valuable in general. Lower priority here: the parsers are grammar-driven against a
small set of fixed emitter format strings, and the campaign's own defects in this
area (string parity, MUX fail-open) were found by targeted attack, not by random
input. Fixed vectors plus X3 likely dominate.

### X10. STPA hazard analysis — *honest downgrade*

`DEVICE_ACTION_RISK_TIERS.md` plus the absolute forbidden-primitive list already
covers the device-safety envelope at the granularity that matters, and the
prohibitions are stated as primitives rather than intentions, which is the part
STPA usually has to fight for. Not worth the ceremony here.

### X11. Pre-mortem before any F1

**Practice:** before the action, assume it has already failed and write down why.

**Why here:** cheap, matches the attended-only posture, and the campaign's F1
gating already requires an exact predeclared recovery — a pre-mortem is the step
that finds the recovery's gaps *before* it is the only option.

---

## Part 4 — The corpus problem

As of 2026-08-21: **2,465** reports, **1,333** test files, **543** ledger rows
across two campaigns, **54** incidents, **5,481** commits since 2025-11-13.

The ledger is queryable and it is the reason the accounting works at all. Almost
nothing else is. Of the 54 incident reports, **42 have no cause-section heading at
all**. The 12 that do are split across **6 distinct heading keywords** in **8
distinct full headings**: `## Root cause`, `## Root Cause`,
`## Root cause and repair boundary`, `## Cause`, `## Failure`,
`## Failure mechanism`, `## What happened`, `## Analysis`. The corpus therefore
cannot answer "what class of thing bites us most?" — a question it plainly
contains the answer to.

This is the highest-leverage structural improvement available, and it does not
require touching anything that exists:

**Add frontmatter to new reports and incidents only. No backfill.**

```yaml
---
target: s22plus-fyg8 | a90 | s20plus
unit: p319
kind: incident | review | design | closure
cause_class: wrong-binding | pass-constant | proposition-inflation |
             fail-open | narrow-sample | recollection | shared-state | schema
detected_by: host-test | independent-review | device-symptom | none
---
```

Six months of that answers X2 and X7 directly, and turns the report corpus from an
archive into evidence. Backfilling 2,465 files is not worth it; the next hundred
are.

---

## Part 5 — Ranked, with cost

| | Action | Cost | Kills |
|---|---|---|---|
| 1 | **X1** provenance record per output directory | one JSON at build time | I1, the defect closest to a bad device action |
| 2 | **P3** every constant derived or justified | per constant | I2 |
| 3 | **X2 / Part 4** frontmatter on new reports | one block per file | makes the corpus answer questions |
| 4 | **P2** each audit declares a mutation that must break it | one test per auditor | I2, I4 |
| 5 | **P1** independent re-derivation before review | reviewer time | mis-review, anchoring |
| 6 | **X6** threshold of three for a frame audit | free | month-long dead ends |
| 7 | **X4** severe-testing question at review | free | pass constants generally |
| 8 | **X5** discriminating tree written before each unit | free | confirmatory units |
| 9 | **X7** confidence per claim | one integer | reviewer calibration |
| 10 | **X3** automated mutation score | moderate build work | I2, I4 systematically |
| 11 | **X11** pre-mortem before F1 | one page | recovery gaps |

Items 6 through 9 are free and unadopted. Start there.
