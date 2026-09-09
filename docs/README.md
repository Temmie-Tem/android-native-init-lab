# Documentation index

**English** · [한국어](README.ko.md)

A map of what is in `docs/` and, more importantly, of **which file is
authoritative for what**. This index deliberately carries no current state: no
latest build, no current unit or P number, no functional version. Those move,
and a second copy of them here would be wrong within days. Every pointer below
is to the file that owns the answer.

The previous Korean index, which did carry that state, is preserved byte for
byte at
[`archive/documentation/DOCS_README_KO_LEGACY_2026-09-09.md`](archive/documentation/DOCS_README_KO_LEGACY_2026-09-09.md).

## Where current state lives

| Question | Authoritative source |
| --- | --- |
| What is the current frontier, active bounded unit and functional version for a target? | [`GOAL.md`](../GOAL.md) (S22+), [`GOAL_A90.md`](../GOAL_A90.md), [`GOAL_S20PLUS.md`](../GOAL_S20PLUS.md) |
| What is a device allowed to do, and under what approval? | [`AGENTS.md`](../AGENTS.md) and the [target contracts](operations/targets/) |
| What did one run actually establish? | that run's report in [`reports/`](reports/) |
| What has a target established overall, and what is still unproved? | [`devices/README.md`](devices/README.md) and the per-device pages |
| How are versions, candidates and runs named, and which artifacts does a version map to? | [`operations/S22PLUS_FYG8_VERSIONING.md`](operations/S22PLUS_FYG8_VERSIONING.md), [`operations/VERSIONING_POLICY.md`](operations/VERSIONING_POLICY.md) |
| What may appear in the public tree? | [`operations/PUBLIC_TREE_SANITIZATION_POLICY.md`](operations/PUBLIC_TREE_SANITIZATION_POLICY.md) |

A summary page never overrides one of these. Where a rolling summary and a GOAL
or contract disagree, the GOAL or contract is right and the summary is stale.

## Reading order

**First time here.** Start with the root [`README.md`](../README.md) for what
the project is, then [`devices/README.md`](devices/README.md) for what each
target has established under a shared evidence vocabulary, then a visual
evidence page if you want to see it rather than read it:
[A90](devices/A90_VISUAL_EVIDENCE.md),
[S22+ display](devices/S22PLUS_DISPLAY_VISUAL_EVIDENCE.md),
[S22+ boot HUD](devices/S22PLUS_BOOT_HUD_VISUAL_EVIDENCE.md).

**Before touching a device or reviewing work that does.**
[`AGENTS.md`](../AGENTS.md) first, then
[`operations/DEVICE_ACTION_RISK_TIERS.md`](operations/DEVICE_ACTION_RISK_TIERS.md),
[`operations/DEVICE_ACTION_PROCESS_V2.md`](operations/DEVICE_ACTION_PROCESS_V2.md)
and the selected [target contract](operations/targets/). The relevant `GOAL*.md`
tells you what the current unit is; it grants no authority by itself.

**Picking up in-flight work.** The target's `GOAL*.md`, then its campaign ledger
in [`operations/`](operations/), then the newest reports for that target.

**Engineering practice.**
[`operations/ENGINEERING_INVARIANTS.md`](operations/ENGINEERING_INVARIANTS.md)
for the cross-target build, addressing and record-keeping invariants;
[`operations/DEVELOPMENT_LOOP_STANDARD.md`](operations/DEVELOPMENT_LOOP_STANDARD.md)
for the A90-specific loop.

## Collections

| Directory | What is in it | Entry point |
| --- | --- | --- |
| [`devices/`](devices/) | Per-device pages and visual evidence, English and Korean | [`devices/README.md`](devices/README.md) |
| [`operations/`](operations/) | Contracts, risk tiers, the device-action process, per-target contracts, capability specs, campaign ledgers, runbooks | listed below |
| [`operations/targets/`](operations/targets/) | The binding per-target contracts | one per target |
| [`reports/`](reports/) | Immutable per-run and per-cycle evidence, thousands of files | by filename, see conventions |
| [`plans/`](plans/) | Designs and handoffs written before a unit runs | by filename |
| [`module-map/`](module-map/) | Subsystem research maps | [`module-map/s22plus-fyg8/README.md`](module-map/s22plus-fyg8/README.md) |
| [`overview/`](overview/) | Project history and versioning narrative | [`overview/PROJECT_HISTORY.md`](overview/PROJECT_HISTORY.md) |
| [`security/`](security/) | Review findings, hardening notes, batches | [`security/README.md`](security/README.md) |
| [`artifacts/`](artifacts/) | Generated inventories and frontier candidate data | [`artifacts/README.md`](artifacts/README.md) |
| [`images/`](images/) | Published photographs and clips referenced by the visual evidence pages | the pages that use them |
| [`archive/`](archive/) | Superseded documents, retired contract text, historical snapshots | [`archive/README.md`](archive/README.md) |

`reports/` and `plans/` are not catalogued here. They grow with every unit, and
a hand-maintained list of them would be stale before it was useful.

### Frequently opened operations documents

- [`operations/DEVICE_ACTION_RISK_TIERS.md`](operations/DEVICE_ACTION_RISK_TIERS.md) — validation effort proportional to the action
- [`operations/DEVICE_ACTION_PROCESS_V2.md`](operations/DEVICE_ACTION_PROCESS_V2.md) — the reusable boot-only process
- [`operations/DEVICE_ACTION_CONTRACT_DETAILS.md`](operations/DEVICE_ACTION_CONTRACT_DETAILS.md) — permanent device safety boundaries
- [`operations/ENGINEERING_INVARIANTS.md`](operations/ENGINEERING_INVARIANTS.md) — cross-target engineering invariants
- [`operations/PUBLIC_TREE_SANITIZATION_POLICY.md`](operations/PUBLIC_TREE_SANITIZATION_POLICY.md) — identifier boundary and the boundary check
- [`operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md`](operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md) — flash and bridge procedure
- [`operations/CLAUDE_NATIVE_INIT_RUNBOOK.md`](operations/CLAUDE_NATIVE_INIT_RUNBOOK.md) — operator runbook

## Finding a report without a catalogue

Report filenames encode where they belong, so grep is the index:

```text
<TARGET or SERIES>_<UNIT>_<TOPIC>_<DATE>.md

S22PLUS_FYG8_P376_BOOT_HUD_H0_2026-09-09.md
NATIVE_INIT_V3043_DOOMGENERIC_LATENCY_COLOR_LIVE_2026-06-22.md
```

Target and series prefixes in use include `S22PLUS`, `A90`, `S20PLUS`,
`NATIVE_INIT`, `KERNEL` and `SERVER`. The date suffix is the report date, not
the run date, when the two differ.

## Archive

Nothing under [`archive/`](archive/) is an active source of device
authorization. Historical `ACTIVE` strings, approval tokens and status claims
inside it are inert evidence. It holds retired contract text, the pre-2026
document generation, and byte-identical snapshots of documents that were
replaced, each recorded with its SHA-256 in
[`archive/README.md`](archive/README.md).

## Language

Device pages, the root README and this index are maintained in English and
Korean. The English file is the structural canonical for each pair; the Korean
counterpart follows its section skeleton and may carry additional local detail.
Operations documents, reports and plans are single-language.
