# S22+ FYG8 P3.19 Process-v2 offline-ready H0 closure

Date: 2026-08-30 KST

## Scope

This is a host-only registration and packaging unit for the exact P3.19 stock
witness candidate. It registers the reviewed candidate-static schema in the
shared Process-v2 evidence verifier, materializes the three private offline
contract artifacts, and creates one tracked `ready-for-f1-approval` manifest.
It performs no device command, approval, transfer, reboot, or recovery action.

The target remains `SM-S906N/g0q/S906NKSS7FYG8`. The candidate and rollback
AP identities remain respectively `db5666ac…` and `d2373bf8…`; both are
boot-only archives with the permitted `boot.img.lz4` member.

## Final authority chain

- raw-first receipt `-19`: 15,075 bytes / `7addbe2a2da4c57e…`, mode 0400,
  link count one. The independently preserved predecessor is `-18`
  `15075B/0ffd6306…`.
- prerequisite receipt `-04-p319-ready-declaration-final`: 13,111 bytes /
  `4f36e5d8a30b5d49…`, mode 0400, link count one.
- Integration V2 `-09`: 125,924 bytes / `664a8354456f5edd…`, mode 0400,
  link count one, zero blockers, `SOURCE_CLOSURE_PASS_RUNTIME_CLASSIFICATION_PENDING`.
- candidate-static `-05`: 34,892 bytes / `9504905e3ed0ac12…`, mode 0400,
  link count one.
- promotion `-05`: `candidate-static.json` `34892B/9504905e…`,
  `run-manifest.json` `1043B/af09b4c0…`, and
  `static-check-result.json` `1842B/25691094…`; all are direct
  mode-0400, link-count-one files.
- tracked ready manifest: 2,432 bytes / `fedb4eef51e5f6d9…`, mode 0400,
  link count one, schema `device_action_f1_candidate_v2`, status
  `ready-for-f1-approval`.

The ready manifest contains no candidate observer because the P3.19 ACM path
is supplemental. The retained Carrier is the required result channel. The
shared verifier independently decodes the exact AP and its generic ramdisk,
checks the 73-row plan and EUD index 38, binds the exact init/child/latch and
adapter sources, and accepts only the three reviewed terminal mappings.

`COMPLETE` remains `NONCAUSAL_SUCCESS_PATH`; it is not candidate proof.
`INCOMPLETE` remains `NO_PROOF_EXPERIMENT_PRECONDITION`, and `AMBIGUOUS`
remains `NO_PROOF_OBSERVER`. All candidate-success, causal-result, MUX, and
host-silent claims remain false. The four runtime witnesses remain required
post-run facts and are not preflight facts.

## Reproduced integration seams

The first ready rehearsal exposed a real ordering seam. The prerequisite had
treated any public occurrence of the new live run ID or candidate digest as a
consumption event, so the ready manifest made its own upstream receipt
non-reproducible. The repair distinguishes the exact non-consuming
`ready-for-f1-approval` declaration from private prepared, journal, claim, and
registry state. Only that exact schema, target, candidate, rollback,
observation identity, and typed three-artifact path grammar is exempted; any
other occurrence still fails closed. The consumption-population counts use
the same projection, so prerequisite bytes are identical before and after
manifest publication.

The check also caught that the final manifest uses the exact `-55` candidate
path, not the older byte-identical `-49` qualification path. The final path is
now checked explicitly. Promotion artifact digests are not pinned inside the
prerequisite because that would create a circular authority; their paths and
typed identities are checked there, while their exact bytes are pinned and
reopened by the downstream common `verify_bundle()` gate.

An exact-regeneration attempt additionally reproduced stale Python bytecode
loading after rapid same-size source edits. The candidate-static local loader
now stable-reads, compiles, and executes the source bytes directly instead of
using an importlib loader that may accept a stale `.pyc`.

Intermediate private `-06/-07/-08`, candidate-static `-02/-03/-04`, and
promotion `-01/-02/-03/-04` artifacts remain preserved as non-authoritative
predecessors. They grant no authority and are not referenced by the final
manifest.

## Validation and boundary

The final manifest-present chain passes 59/59 focused tests, including exact
regeneration of prerequisite, Integration V2, candidate-static, promotion,
and manifest bytes; hostile type, proof-class, plan, AP, declaration-shape,
and no-clobber checks; and real C encoder-to-Carrier-to-decoder terminal
arming. Common Process-v2 tests pass 142/142, and the additional P3.18/P3.19
adapter/registration/arming regressions pass 25/25 (167/167 combined).

This unit creates a review-pending H0 capability only. It creates no approval,
no prepared live run, no consumed-candidate claim, and no D0, D1, F1,
recovery, replay, or unattended authority. Independent changed-closure review
is required before the manifest may be presented for a fresh attended F1
approval.
