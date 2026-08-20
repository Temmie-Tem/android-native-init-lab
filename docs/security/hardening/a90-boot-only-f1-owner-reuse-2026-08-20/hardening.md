# Security Hardening Review: A90 reusable boot-only F1 owner

> **SUPERSEDED 2026-08-20.** The selected sealed-package implementation was
> retired before activation because its host-runtime closure was
> disproportionate. See
> `docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md`. This portfolio
> remains historical evidence and grants no authority.

## Evidence Basis

We reviewed the A90 F1 policy, current owner/contract/observer, runtime
qualification, focused tests, and existing serial-to-recovery flash helper at
revision `2a5ec435dc3203fd78a55b3ab33440bedd785590`. The 12-file evidence
collection is recorded in [context.md](context.md) with aggregate SHA256
`4e0f73012dbb9b92fefca94780ab4c7f1660a0ad9ff0cb54d42e8e483f57692c`.

One current focused result is especially useful: 75 of 76 tests passed, while
the remaining failure came from host Python runtime-tree drift even though the
owner closure still matched its stored value. This is host-only design evidence,
not a device result.

## Constraints

- A90 and boot-only F1 only; no generic device framework.
- Reuse existing Native serial, TWRP recovery ADB, `a90ctl`, bridge, and flash
  helper.
- Preserve exact target/artifact binding, intent-before-effect, candidate and
  rollback one-shot semantics, and serial final health.
- Optimize for repeated kernel experiments and low review churn.
- Root and malicious same-UID concurrency remain outside the lane.
- This analysis grants no D0, D1, F1, candidate, or live authority.

## Opportunity Portfolio

| Opportunity | Evidence | Options | Recommendation | Proposal |
| --- | --- | --- | --- | --- |
| Align owner identity with A90 effect authority | F1 invariants, test-in-closure coupling, measured host-runtime drift, existing recovery helper | Correct current strong closure; stable A90 owner package; static owner binary | Stable A90 owner package under the current trusted-host and repeated-experiment constraints | [Stable A90 boot-only F1 owner boundary](proposals/a90-f1-owner-reuse-boundary.md) |

## Recommendation Summary

I recommend the stable A90 owner package. We should keep the controls that can
prevent or repeat a boot write, but move tests, reviews, historical evidence,
and broad host runtime trees outside the execution digest. One package, one
owned serial bridge, one four-command observation worker, the existing
recovery-only ADB helper, and a small journal resume table are enough.

The operator selected this option on 2026-08-20. The ordered H0 migration is
recorded in the [implementation plan](implementation/stable-a90-owner-package.md).

The current stronger closure remains a fair choice for a locked workstation
where exact host reproducibility outweighs experiment speed. A static binary is
the cleaner long-term boundary but is not proportionate before we know the
remaining A90 campaign length.

## Next Decisions

1. Complete the remaining stable-package work packages without enabling live
   execution.
2. Decide whether recovery ADB serial is stable or must be bound by exact-one
   USB arrival/topology.
3. Freeze and independently review the final execution closure before any
   candidate preparation or F1 authority.
