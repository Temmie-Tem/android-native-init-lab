# S22+ FYG8 P3.19 D0 fresh-baseline V3 repin

Date: 2026-08-29

Status: **IMPLEMENTED / REVIEW PENDING / NOT ACTIVE**

## Result

The exact `d1-fresh-baseline-3` run is now a valid consumed predecessor. It
performed one normal Android reboot and retained a 39,594-byte result with
SHA-256 `8dc828d3`. The result proves a changed boot identity, healthy rooted
FYG8 before and after, stable selected serial and topology, complete raw
evidence, and zero other-target commands. Candidate transfer, device writes,
Download, Odin, partition payload, F1, live authority, and replay are false.
The outer pre-F1 journal is `CLOSED` with one D1 effect; its 1,287-byte close
record has SHA-256 `ea7de807`.

The first prepare invocation stopped before device contact because the exact
private campaign parent did not yet exist. Creating only that fixed directory
as current-owner mode 0700 was the single bounded host preparation repair. No
source or binding changed, and the corrected prepare was the only re-entry.

## Minimal V3 successor

The prior D0 V2 source and reducer are permanently bound to the consumed
`d1-fresh-baseline-2` namespace and cannot consume the V3 result. They remain
byte-preserved. The successor therefore adds two versioned files rather than
rewriting reviewed history:

- D0 producer: 73,378 bytes / `a8b902e1`;
- normalized reducer: 70,596 bytes / `db184e14`;
- pending execution binding: 14,504 bytes / `c751815b`.

The D0 namespace is separate from the D1 parent because D1 V3 permits only its
fixed arm and run children. The D0 behavior itself is unchanged: one exact
2,097,136-byte `/proc/last_kmsg` read, immutable raw-first parsing, fixed exact
target/current-boot continuity, zero other-target commands, typed consumed
stop on uncertainty, and no write, reboot, Download, Odin, payload, or F1.

The reducer does not reproduce the D1 result grammar. It compiles the exact
reviewed D1 V3 source and requires `_validated_static_inputs()`,
`_validated_execution_inputs()`, and `_post_validate()`. The caller-provided
result must be canonical-equal to that reopened result, after which the exact
result, D1 source, and D1 binding are read once more. V1/V2 paths, substituted
health, and forged raw inventory fail closed.

## Raw-first boundary

The new producer is registered as the twentieth active observer source. The
76,334-byte auditor has SHA-256 `75231c68` and normalized self-hash `5e9f0763`.
Its 15,075-byte `b70ac022` receipt is mode 0400/link-count one and preserves the
128-member pre-boundary and 126-member closed-observer inventories. The source
census changes only from 1,744 to 1,746 for the two new Python files;
subprocess-module census remains 412. Receipt `-12` and all predecessors remain
unchanged.

## Validation and boundary

Focused V3 tests pass 11/11. They reopen the actual D1 V3 result, reject V2
paths and forged health/raw data, keep review and approval checks before
acquisition, exercise one exact raw-first read, reject short/stderr/nonzero
captures and target/topology/boot drift, and preserve consumed no-replay arm
state. Raw active-source seams and deterministic documentation pass 22/22.

The binding remains `review-pending`. No D0 approval, arm, device read, result,
or normalized baseline exists. Process-v2 integration remains
`FRESH_BASELINE_MISSING`; its V3 repin belongs after a reviewed D0 result, not
inside this implementation unit. Independent changed-closure review is still
required, and F1 remains separately attended.
