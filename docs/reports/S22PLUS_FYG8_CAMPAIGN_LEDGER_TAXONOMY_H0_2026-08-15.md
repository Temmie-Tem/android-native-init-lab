# S22+ FYG8 campaign-ledger taxonomy H0 — 2026-08-15

Status: **FOLLOWUP IMPLEMENTED_REVIEW_PENDING; H0 ONLY; NO LIVE AUTHORITY**

## Scope

This host-only unit separates five meanings that the append-only ledger had
partly carried in one proof column:

1. immutable row-local evidence outcome;
2. row kind and device-attempt phase;
3. effective experiment proof;
4. device health; and
5. H0 capability review state.

It changes no historical log row, candidate, P3.18 execution-critical byte,
`SOURCE_KEYS`, package, ready manifest, device state, or target contract. It
grants no D0, D1, F1, recovery, replay, or live authority. The append-only
review-7 verdict remains historical authority only for its earlier exact
closure. This follow-up changes taxonomy derivation and requires a fresh
independent review.

## Metrics boundary

A normalized F1 attempt enters experiment-metric denominators exactly once
when its maximum candidate-transfer count reaches one. `CAMPAIGN_CLOSED` adds
the terminal experiment proof; it is not the eligibility condition. A
candidate-bearing attempt without a close remains `ATTEMPT_OPEN`, contributes
to the denominator, and contributes nothing to a conclusive numerator.
Intermediate F1/recovery rows, pre-session stops, D0/D1 rows, H0 work, and
correction rows do not independently add attempts. Their proof-column spelling
remains immutable row evidence, but it does not silently become an experiment
verdict.

The audit therefore excludes the P3.14 zero-transfer pre-session Download stop
and counts the P3.17 `ROLLBACK_ENDPOINT_AMBIGUITY_PARK` plus later
`1-recovery-close` as one attempt, not two.

## Correction scope

The ledger header now carries two explicit machine-readable correction rows:

- P3.16 ordinal 1 is `CAMPAIGN_PROOF`; its immutable raw terminal remains
  `NO_PROOF_OBSERVER`, while its effective experiment class is
  `NO_PROOF_EXPERIMENT_PRECONDITION` and changes metrics once.
- P3.17 ordinal 1 endpoint selection is `SUBRESULT_ONLY`; it records the
  physical-topology precondition failure without replacing the campaign's
  `MAX77705_RESULT_MULTIPLICITY` terminal or changing campaign metrics.

That distinction produces the already-audited P3.10–P3.16 cohort of four
observer no-proofs, one experiment-precondition no-proof, and two conclusive
results. Adding P3.17 produces five observer no-proofs, one precondition
no-proof, and two conclusive results. The corresponding conclusive yields are
2/7 and 2/8; diagnostic-bearing yields are 3/7 and 3/8.

The observer-localization sources for P3.10, P3.11, P3.13, and P3.14 are
rechecked from their immutable terminal/post-live rows, including both P3.13
decoder and stop-multiplicity localizations. P3.17's campaign class is
independently tied to `MAX77705_RESULT_MULTIPLICITY`.

## Review-state boundary

Review status is not experiment proof. For H0 rows, an action beginning
`PASS_GO_` is `PASS_GO`; an action ending `_REVIEW_PENDING` or
`_PENDING_REVIEW` is `IMPLEMENTED_REVIEW_PENDING`. Older action names that
merely contain `REVIEW` remain `LEGACY_UNSCOPED_REVIEW_LABEL`; approval is not
inferred from the word. Through the implementation row the audit finds 20 raw
`PASS_GO` labels, 11 raw pending labels, four legacy-unscoped labels, and 147
not-applicable rows. These are historical label counts, not review debt.

Review obligations use `(campaign, review-topic)` keys rather than campaign
alone. Unrelated pending topics may remain open in parallel, while only an
`h0-<same-topic>-review-N` PASS row can resolve one. Six frozen historical
nonconforming pairs are exact identity exceptions. At the frozen
implementation scope, ten of eleven obligations are resolved and the taxonomy
implementation itself is the one open obligation. Review-7 resolves that
obligation in the append-only tail. Before this follow-up, all eleven
historical obligations were therefore resolved; the new follow-up row
intentionally creates one fresh unresolved `ledger-taxonomy` obligation.

Ten of the 20 scoped `PASS_GO` labels resolve no pending obligation: P3.09,
P3.11, P3.12, P3.13, two P3.14 rows, P3.15, P3.16, and two P3.18 rows. The
receipt exposes them as `pass_go_resolving_no_obligation`; therefore this axis
measures compliance with explicit pending-label discipline, not universal
review coverage for every capability ever shipped.

H0 row kind no longer consumes this classifier. It distinguishes only the two
exact machine-registered correction rows from other host-only work; action
substrings such as P3.09's `CORRECTION_PREREQUISITE` grant no correction kind.
This H0 kind is intentionally coarse, while review state remains a separate
axis rather than being relabeled as kind.

The four legacy-unscoped labels grant no machine-scoped approval. This includes
the `FOCUSED_INDEPENDENT_REVIEW` rows for P3.01 and P3.05; both campaigns are
historically closed, so this stricter interpretation creates no current live
authority or device effect.

## Append-only and schema closure

The 181 log rows preceding this implementation are preserved as exactly
103,274 bytes with SHA-256
`3c0cca0feea9259a0107cc9c9bfa021579707595afa15b6bf9371529f1fe06e1`.
The parser requires nine fields for every row except four exact historical
eight-field rows. Those four findings already state that no transfer occurred;
the audit normalizes only those exact identities to `0/0` and rejects any
other missing transfer field. Four exact historical rows retain the legacy
`NO_PROOF`, `NO_PROOF_SUBTYPE`, or `NO_PROOF_LOG_BASELINE` evidence spelling;
the parser rejects those spellings on every other row.

The taxonomy scope ends at
`s22plus-fyg8-p318/h0-ledger-taxonomy-7`; later append-only review rows are not
retroactively folded into this implementation receipt. They are nevertheless
fully schema-validated, so a valid post-scope row leaves the receipt unchanged
while a missing transfer field, legacy spelling reuse, or conflicting review
state fails closed. UTC timestamps must also parse as real calendar dates and
times rather than merely matching the textual shape or regressing append
order; equal timestamps remain valid. S22 campaign, ordinal, and action tokens
are closed, each action key is unique, and review-state labels are H0-only.
Non-F1 rows require `0/0`; F1 counts are one-shot, cannot record rollback
without candidate, and candidate-bearing ordinals are positive canonical
integers. `CAMPAIGN_CLOSED` requires exactly one candidate transfer. A healthy
close also requires exact rollback; pending, observer-failure, and parked
health cannot close, while an exhausted `RECOVERY_REQUIRED` close may retain
1/0 or 1/1. All F1 rows sharing one campaign and normalized attempt ordinal
must advance transfer counts monotonically, may contain exactly one terminal,
and cannot continue after it; `-recovery-close` requires a prior base-attempt
row. Candidate-bearing attempts are separately inventoried as `CLOSED` or
`ATTEMPT_OPEN`; the current frozen scope has 19 closed attempts and zero open
attempts, so the published 2/7, 3/7, 2/8, and 3/8 values do not change.

The ledger has no candidate artifact hash or other candidate identity cell.
This taxonomy therefore audits attempt-local count monotonicity but does not
audit candidate artifact identity or cross-ordinal replay. The Process-v2
closure remains the higher-precedence authority for no-replay.

The scoped ledger identity is 110,202 bytes with SHA-256
`5ec56a03bcec560895102447fe4553979719e32551cba7649648bc8fa98b6640`.

## Retained receipt

`workspace/private/outputs/s22plus_fyg8_p318_ledger_taxonomy/ledger-taxonomy-20260815-01.json`

- size: 23,257 bytes
- SHA-256: `6e1fb6cd64879a8b2610861cfe7e4b22a1f0ac470556c178d548c76a090b1c61`
- schema: `s22plus-fyg8-campaign-ledger-taxonomy-v2`
- derivation version: 2
- verdict: `PASS_P318_CAMPAIGN_LEDGER_TAXONOMY_H0_V2`
- status: `IMPLEMENTED_REVIEW_PENDING`
- auditor source: 44,601 bytes,
  SHA-256 `e0dc2051cc51b29f0b83b6a12f2350eeec38e12e987e1eaa3a357e2e48a64a21`

The receipt is deterministically regenerated from one stable read of the
ledger and one stable read of the auditor. Publication is exclusive,
file-synced, and directory-synced. Its safety section records zero device,
candidate, rollback, A90, and S20+ actions and explicitly denies live
authority.

The exact review-7 predecessor receipt is separately preserved at
`workspace/private/outputs/s22plus_fyg8_p318_ledger_taxonomy/ledger-taxonomy-20260815-01-v1-approved.json`
(10,118 bytes, SHA-256 `4214ea5393ed…`). Its approved auditor bytes are
not recoverable because that source was untracked and edited in place. The
tracked marker
`docs/reports/S22PLUS_FYG8_P318_LEDGER_TAXONOMY_V1_PREDECESSOR_PROVENANCE.json`
records the predecessor receipt, auditor and scope identities, the 1,080-byte
scope delta, and the exact non-reproducibility reason. Preserved V1 bytes are
historical provenance only, never current authority.

Current implementation validation passes taxonomy 37/37 and the combined
taxonomy/P3.18/Process-v2 documentation set 68/68. Common Process-v2 passes
120/120: `test_device_action_f1_v2` 22, `test_device_action_f1_evidence_v2`
28, `test_device_action_f1_live_v2` 45, and
`test_device_action_process_v2_docs` 25. The full P3.18 set passes 136/136.

## Predecessor independent review

The review-7 read-only reviewer independently regenerated the predecessor receipt
byte-for-byte and attacked the complete future tail schema. It rejected the
five normalized-attempt state failures (two terminals, rollback regression,
candidate regression, post-close continuation, and orphan recovery-close)
while preserving the P3.17 base `1/0` to recovery-close `1/1` transition.
That verdict remains valid only for the predecessor hashes and does not approve
this follow-up.

## Remaining boundary

This follow-up is implemented but not independently approved. It does not alter
P3.18 candidate bytes, prepare a run, or create D0, D1, F1, recovery, replay,
live, or device authority. The next permissible step is read-only independent
review of this exact changed closure; device work is neither required nor
authorized.
