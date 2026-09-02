# P3.20–P3.22 — consumed F1 runs absent from the campaign ledger

Date: 2026-09-02
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`
Tier: H0 process audit
Device contact: none — zero ADB, USB, Odin, reboot, transfer, rollback or replay
Authority: none. This audit writes no F1 row, alters no consumed run, and
creates no replay, recovery, or device authority. It records a divergence; it
does not repair one.

## Summary

Three consumed F1 campaigns — P3.20, P3.21 and P3.22 — have no F1 row in
`docs/operations/CAMPAIGN_LEDGER_S22PLUS.md`. The machine-checked attempt
inventory over the whole ledger therefore reads 25 attempts at
`candidate=25 rollback=25`, where the retained evidence supports 28/28.

This is **not** an unrecorded device action. The substantive record is complete
and explicit in prose, and the retained run evidence is intact for all three.
What is missing is the machine-readable row, which is the form the taxonomy
auditor consumes.

## The gap

`audit_attempt_inventory` is called on `all_rows`, not on the P3.18-scoped
subset (`s22plus_fyg8_campaign_ledger_taxonomy.py:1023`), so this is a live
whole-ledger check rather than a frozen receipt.

| | |
|---|---|
| attempts in inventory | 25 |
| candidate transfers counted | 25 |
| rollback transfers counted | 25 |
| supported by retained evidence | 28 / 28 |

F1 rows run unbroken from `s22plus-fyg8-p296` through `s22plus-fyg8-p319` —
twenty-one campaigns, each with its own `CAMPAIGN_CLOSED` row. The next F1 row
is `s22plus-fyg8-p323` at `2026-09-01T10:22:43Z`. Between
`2026-08-30T08:34:52Z` and that row there is nothing.

| campaign | ledger rows | F1 row | consumed run |
|---|---|---|---|
| p319 | 210 | `1 / CAMPAIGN_CLOSED / 1-1` | yes |
| p320 | 1 (H0 only) | **none** | yes |
| p321 | 0 | **none** | yes |
| p322 | 0 | **none** | yes |
| p323 | 2 | `1 / CAMPAIGN_CLOSED / 1-1` | yes |

## Control cases

The absence of an F1 row is not by itself a defect — a host-only campaign
correctly has none. `s22plus-fyg8-p302` and `s22plus-fyg8-p309` carry ledger
rows, no F1 row, no F1 report, and no consumed-run statement in `GOAL.md`.
They are the shape a campaign without a device run should have, and they
confirm the finding is specific to P3.20 through P3.22 rather than an artifact
of how the ledger records host-only work.

## What does record these runs

`GOAL.md` carries all three, with transfer counts, health, formal terminal, and
an explicit no-replay statement for each:

- P3.20 — "closed and consumed after one candidate/rollback transfer and
  healthy return", terminal `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` /
  `NO_PROOF_OBSERVER`.
- P3.21 — "remains closed and consumed after exact candidate/rollback transfers
  and healthy rooted FYG8 return … P3.21 is never replayable."
- P3.22 — "remains a closed consumed predecessor with exact 1/1 transfers and
  healthy return … P3.22 is never replayable."

Each also has its own report:
`S22PLUS_FYG8_P320_F1_MIXED_RUN_NO_PROOF_2026-08-30.md`,
`S22PLUS_FYG8_P321_F1_BAD_BODY_NO_PROOF_2026-08-31.md`,
`S22PLUS_FYG8_P322_F1_OBSERVER_NO_PROOF_2026-08-31.md`.

So the no-replay claim is stated, sourced, and per-campaign. The exposure is
narrower than a missing record: an automated transfer or replay check over the
ledger undercounts by three candidates and three rollbacks, and any future
reader who trusts the machine-readable accounting over the prose gets the wrong
number.

## Retained evidence — remediation is possible for all three

All three run directories survive under
`workspace/private/runs/device-action-f1-live-v2/`, 32 files each, and each
carries everything a `1/1 CAMPAIGN_CLOSED` row would need:

| run directory | campaign |
|---|---|
| `p320-ready1-prepared-20260830-1` | P3.20 |
| `p321-ready1-prepared-20260831-3` | P3.21 |
| `f1-2026-08-30T205111789065Z-1788123071789099897` | P3.22 |

`live-result.json` in each: `current_state = CLOSED`,
`verdict = NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`,
`outcome_class = p32X_observer_no_proof_rollback_verified`,
`recovery_required = false`.

`live-state.json` in each: `candidate_classification = odin_transfer_completed`
with `candidate_completed = true`, and `rollback_classification =
odin_transfer_completed` with `rollback_completed = true`.

Transfer counts of 1/1 are therefore machine-derivable from retained evidence
for all three, not reconstructed from prose.

Two incidental observations from locating them:

- The P3.22 directory does not follow the `p32X-ready1-prepared-<date>-N`
  convention the other two use; it is named `f1-<timestamp>-<id>`, and its
  embedded timestamp reads 2026-08-30 while the report is dated 2026-08-31.
  A search by campaign name does not find it. This audit initially failed to
  locate it for exactly that reason and the earlier conclusion was wrong.
- P3.21 has three prepared directories. `-1` and `-2` contain only `preflight`
  and appear to be pre-candidate aborts; `-3` is the consumed run. Under the
  ordinary contract a pre-candidate abort is a `0/0` row, so those two are also
  unrecorded, though at no transfer cost.

## What this audit does not do

It writes no F1 row. Adding device-effect rows to an append-only record after
the fact is a decision about that record's integrity, and it belongs to the
operator rather than to whichever session happens to notice. Two dispositions
are available and both are defensible:

1. Append three retrospective `CAMPAIGN_CLOSED` rows derived from the retained
   `live-result.json` / `live-state.json` of each run, each marked in its own
   text as recorded retrospectively on 2026-09-02, naming the run directory it
   was derived from. This restores 28/28.
2. Record an explicit accepted divergence: the ledger stays short by three, on
   the stated grounds that `GOAL.md` and the retained Process-v2 evidence carry
   the transfers and the no-replay statements, and that the ledger row schema
   holds no candidate artifact identity in any case.

What should not happen is the third option, which is what currently obtains:
neither row nor recorded acceptance.

## Forward risk

`s22plus-fyg8-p327` has zero ledger rows as of this audit and is the campaign
under construction. This is preventable rather than historical, and it has been
raised with the session building it.

## Limitations

- The three runs were not re-derived, re-executed, or verified against the
  device. `live-result.json` and `live-state.json` were read as retained
  evidence and their internal consistency was not audited.
- Whether P3.21's `-1` and `-2` are genuinely pre-candidate aborts is inferred
  from directory contents, not from a journal read.
- Campaigns before P3.19 were checked only for the presence of an F1 row, not
  for agreement between that row and their reports.
