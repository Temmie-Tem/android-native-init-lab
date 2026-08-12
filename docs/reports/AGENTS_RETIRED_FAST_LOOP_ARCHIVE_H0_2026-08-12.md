# Retired Fast-Loop contract archive

Status: **H0_IMPLEMENTED_INDEPENDENT_CONTRACT_REVIEW_PASS_GO**

This is a repository-contract shape change only. It grants no device authority,
changes no permanent safety boundary, and performs no device action.

## Trigger

`03f4b3461fe84c487af8d344c4e86b07f8384b3f` added the reviewed S20+
binding-registry row to `AGENTS.md`. Its parent had exactly 260 lines and the
commit had 261, so `test_active_contracts_remain_small` correctly failed the
260-line hard limit. P3.17 exposed the red common regression but did not cause
it.

The excess line was not removable current authority. The safe compression
target was the already retired historical trial block at the former lines
5-86. The current authority preamble and default work cycle at the former
lines 88-100 remain active and were not archived.

## Transformation

- The former 82-line, 4,898-byte retired block is preserved exactly at
  `docs/archive/policy/AGENTS_INTERIM_FAST_LOOP_RETIRED_2026-08-03.md`.
- Its SHA-256 is
  `e270865908821ff1221665a83a22707ae0dcde140e18e5ba600b82423c34dbc7`.
- A byte comparison against lines 5-86 of
  `bfe64b345ab6d9f9d6ee119327e587e7afe3fcc7:AGENTS.md` is exact.
- Root `AGENTS.md` retains one non-authoritative pointer and falls from 261 to
  180 lines, below both the 220-line review threshold and 260-line hard limit.
- The active tail beginning with the former line 88 is byte-identical, SHA-256
  `474ad4b4ddbcab9569a38ba83c61b9f537688d7d5b7853a26c72b8bea3497eb6`.
- The archive index states that the moved block is inert historical evidence
  and grants no current authority.

The documentation regression now reads retired-trial assertions from the
archive, pins the exact archive hash and 82-line extent, requires the root
pointer, and continues to test current authority against root `AGENTS.md`.

## Boundaries

No S22+, A90, or S20+ device was contacted. No target contract, target registry
row, approval rule, transfer path, rollback identity, evidence schema, runner,
manifest, or permanent boundary changed. Existing unrelated A90 worktree edits
were preserved and are outside this change.

Independent review confirmed the byte-preserving move, unchanged active tail,
exact 317-byte prefix, archive inertness, test authority split, and absence of
semantic authority change. It returned `PASS_GO` after three fail-open test
gaps were corrected: universal-newline normalization of the archive, an
unpinned active tail, and an unpinned root prefix.
