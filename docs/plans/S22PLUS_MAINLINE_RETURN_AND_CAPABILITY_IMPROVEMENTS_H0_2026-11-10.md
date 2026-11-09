# S22+ return and capability improvements

Status: **IMPLEMENTED IN ISOLATED H0 — NOT LIVE-ADOPTED**.

The two proposals originally separated from stage-two diagnostics were later
selected for H0 implementation. Their implementation and validation are in the
[efficiency report](../reports/S22PLUS_MAINLINE_EFFICIENCY_H0_2026-11-10.md); the
[shared V2 specification](../operations/S22PLUS_MAINLINE_UFS_CAPABILITY_V2.md)
remains `H0_NOT_ADOPTED` and grants no device authority.

The normal-return extension is limited to the actual pre-overlay coverage
refusal with settled references and RPMh context. Stage-two and later failures,
unknown effects and expired windows remain excluded. UFS functional status
stays `NO_PROOF` after a refused operation even if normal Download succeeds.

Capability reuse is limited to fresh keys and deterministic derived identity
and packaging. Changed execution, recovery, authority, health, kernel/module,
configuration, packages or network semantics invalidate the affected binding.
Fresh candidate reproduction and exact artifact qualification remain required.
The selected source closure, complete raw provenance and old consumed records
retain their separate meanings; a review is never a run grant.

The existing guards and 300-second witness are unchanged. Any future live
adoption needs the applicable common/target adoption and reviewed reachable
closure. Changing the witness, allowing record-and-continue after a failed
execution precondition, broad policy cleanup, storage cleanup and the unrelated
Debian boot-journal unit are outside this implemented H0 scope.
