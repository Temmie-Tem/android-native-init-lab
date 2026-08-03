# A90 Campaign Ledger

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
2026-08-02T19:42:06Z | a90-resident-switchroot-display-ssh-20260802 | 1 | D1 | SWITCHROOT_EXPERIMENT | HEALTHY | PROVED | 0/0 | Debian PID1, Dropbear SSH, direct DRM master, and operator-visible DISPLAY OWNER DEBIAN proved; exact resident return and cleanup passed; retained-pmsg observer warning
2026-08-03T04:05:39Z | a90-resident-switchroot-display-ssh-20260802 | N/A | D0 | RESIDENT_D0_PREFLIGHT | HEALTHY | N/A | 0/0 | Exact A90 pin, resident version and build, selftest fail=0, and source precheck exact; no handoff or effect; S22+ untouched
2026-08-03T04:40:04Z | a90-resident-switchroot-display-ssh-20260802 | 2 | D1 | SWITCHROOT_EXPERIMENT | HEALTHY | PROVED | 0/0 | Qualified unattended one-shot proved Debian PID1, Dropbear SSH, direct DRM master, automatic native return, cleanup, and resident health; physical visibility unavailable; no replay; S22+ untouched
2026-08-03T04:49:16Z | a90-resident-switchroot-display-ssh-20260802 | 3 | D1 | SWITCHROOT_EXPERIMENT | HEALTHY | PROVED | 0/0 | Second qualified unattended one-shot repeated Debian PID1, Dropbear SSH, direct DRM master, automatic native return, cleanup, and resident health; physical visibility unavailable; no replay; S22+ untouched
