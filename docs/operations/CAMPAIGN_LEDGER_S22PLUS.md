# S22+ FYG8 Campaign Ledger

Append-only. One line per experiment action or material health/recovery state
transition under the Interim Fast-Loop Rules in `AGENTS.md`. This replaces
per-run prose reports for routine work only. It does not replace the private
structured result, append-only journal, raw logs, or transfer accounting
required by the selected tier and target contract.

For trial retirement, count only the first `CAMPAIGN_CLOSED` action row for
each distinct campaign ID across both ledgers. Duplicate close, parked, and
per-action health rows do not count.

Write a separate report only for a new capability, a new hazard class, an
incident, or a genuinely ambiguous device-safety result.

Metrics:

- information-bearing results per week: `PROVED + REFUTED`;
- information yield: `(PROVED + REFUTED) / all device attempts`; and
- observer no-proof rate: `NO_PROOF_OBSERVER / all device attempts`.

Device safety is recorded independently from experiment proof. A timeout or
late endpoint may be `HEALTH_PENDING`, `HOST_OBSERVER_FAILURE`, or
`RECOVERY_PENDING_PARKED` without closing the campaign.

## Format

`<UTC> | <campaign> | <ordinal> | <tier> | <action> | <HEALTHY|HEALTH_PENDING|HOST_OBSERVER_FAILURE|RECOVERY_PENDING_PARKED|RECOVERY_REQUIRED> | <PROVED|REFUTED|NO_PROOF_OBSERVER|N/A> | <candidate-transfers>/<rollback-transfers> | <one-line finding>`

## Log

<!-- append below; never edit or remove an earlier line -->
2026-08-03T09:07:47Z | s22plus-fyg8-p296 | baseline-rotation-1 | D1 | NORMAL_REBOOT_BASELINE_ROTATION | HEALTHY | N/A | 0/0 | One normal reboot; the original observer timed out with ADB offline, one host transport repair restored observation, boot-id changed, and exact rooted FYG8 health passed with no replay.
2026-08-03T09:08:44Z | s22plus-fyg8-p296 | connected-d0-1 | D0 | CONNECTED_READ_ONLY_BASELINE | HEALTHY | N/A | 0/0 | Exact S22+ clean baseline passed: 2097136-byte last_kmsg read to EOF, zero marker-family matches, exact rooted FYG8 health, and zero A90 commands.
2026-08-03T09:33:20Z | s22plus-fyg8-p296 | process-v2-prepare-1 | D0 | PROCESS_V2_PREPARE | HEALTHY | N/A | 0/0 | Fresh exact S22+ D0 bound the clean baseline, candidate, rollback, manifest, and reviewed execution closure; prepared compatibility binding reopened, F1 remained unarmed, and A90 commands were zero.
2026-08-03T09:45:36Z | s22plus-fyg8-p296 | 1 | F1 | ROLLBACK_DOWNLOAD_WAIT | RECOVERY_PENDING_PARKED | NO_PROOF_OBSERVER | 1/0 | Candidate CDC endpoint timed out; operator saw one boot with no loop, then recovery USB inventory failed during physical handoff; candidate remained consumed with no replay while exact rollback waited for Download.
2026-08-03T09:48:29Z | s22plus-fyg8-p296 | 1 | F1 | CAMPAIGN_CLOSED | HEALTHY | REFUTED | 1/1 | Exact P2.96 generations 106/107 proved USBLNKST=0 then nominal not-attached/UNKNOWN/COREIDLE=1/SUSPHY=0; durable recover sent exact Magisk rollback once and final rooted FYG8 health passed.
2026-08-03T10:17:36Z | s22plus-fyg8-post-p296-attribution | h0-1 | H0 | SOURCE_ATTRIBUTION | HEALTHY | PROVED | 0/0 | Exact source proves the ignored __dwc3_gadget_start return is the earliest unresolved predicate; select one boot-built signed return pair before event or PHY evidence, with zero device commands and A90 untouched.
