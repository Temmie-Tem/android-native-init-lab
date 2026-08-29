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

- raw-first receipt `-23`: 15,075 bytes / `608799f12b16aab5…`, mode 0400,
  link count one. The independently preserved immediate predecessor is `-22`
  `15075B/d6ad008c…`.
- prerequisite receipt `-11-p319-final`: 13,228 bytes / `d0f3fb5b43a52d07…`,
  mode 0400, link count one.
- Integration V2 `-15`: 126,085 bytes / `1542dfb9bf7f1543…`, mode 0400,
  link count one, zero blockers, `SOURCE_CLOSURE_PASS_RUNTIME_CLASSIFICATION_PENDING`.
- candidate-static `-10`: 35,259 bytes / `2425fed6e791e2d7…`, mode 0400,
  link count one.
- promotion `-10`: `candidate-static.json` `35259B/2425fed6…`,
  `run-manifest.json` `1043B/25c3bb09…`, and
  `static-check-result.json` `1842B/83bc6508…`; all are direct
  mode-0400, link-count-one files.
- tracked ready manifest: 2,432 bytes / `2721ede6bc5d45fd…`, mode 0644,
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

Independent hostile review then proved that the first classifier checked only
part of the acceptance identity and only the shape of the three contract
digests. It accepted mutations to decoder, policy, Carrier families, terminal,
minimum count, clean-baseline flag, timeout, and candidate-static digest. The
repair checks every fixed acceptance field, requires timeout 300, and reopens
all three referenced private promotion files as direct mode-0400/link-one
files before comparing their actual sizes and SHA-256 values. This avoids a
source-level circular digest while rejecting all reproduced mutations.

The check also caught that the final manifest uses the exact `-55` candidate
path, not the older byte-identical `-49` qualification path. The final path is
now checked explicitly. Promotion digests are not source-level constants in
the prerequisite because that would create a circular authority; instead the
manifest's typed identities are compared with the reopened private files, and
the downstream common `verify_bundle()` independently repeats exact binding.

Hostile review also proved that the shared P3.19 candidate-static validator
accepted self-consistent but forged nested Integration receipts, candidate
identity fields, and source-key claims. The final candidate-static object now
self-binds its exact builder source. The shared verifier stable-reads and
executes that source, and the builder reopens and freshly regenerates the
bound Integration result before recursively exact-type-comparing the complete
candidate-static object. Shape-only nested provenance is no longer an
authority path.

Python equality also admitted `true`, `1.0`, `73.0`, and `38.0` in integer or
Boolean fields. Exact integer checks now cover the public acceptance terminal,
minimum count and timeout plus the candidate/AP 73-row and EUD-38 plan. The
full-object regeneration rejects Boolean/integer substitutions in runtime and
safety flags.

The prerequisite now reads the current global registry's validated hash-chain
history and reconstructs active claims before reporting candidate absence. The
current authority contains zero records and zero active claims; an active claim
for the P3.19 AP digest fails closed. The live runner still repeats its atomic
preflight immediately before any candidate effect.

Finally, hostile review reproduced a real same-size, same-timestamp stale
`.pyc`: the P310 source contained a changed Carrier family while the imported
module executed the old family, and the predecessor verifier accepted it.
The shared P3.19 loader now stable-reads the complete 39-module local adapter
closure, removes preloaded copies, and executes every member through a
source-only graph loader. The candidate-static loader does the same and
replaces Integration's dynamic local loader with that stable path. A hostile
test recreates the stale bytecode and proves the changed source bytes, not the
cached module, execute.

Intermediate private raw-first `-19` through `-22`, prerequisite `-04` through `-10`,
Integration `-06` through `-14`, candidate-static `-02` through `-09`, and
promotion `-01` through `-09` artifacts remain preserved as non-authoritative
predecessors. Integration `-11/-12` record the correct fail-closed reaction to
an interim adapter identity drift. The unused host-only requalification
`-12/-56/-57` independently reproduced the same candidate bytes but is not
referenced by the final chain. None grants authority.

## Validation and boundary

The final manifest-present chain passes 69/69 focused tests, including exact
regeneration of prerequisite, Integration V2, candidate-static, promotion,
and manifest bytes; hostile nested-provenance, stale-bytecode, exact-type,
proof-class, plan, AP, declaration-shape, and no-clobber checks; and real C
encoder-to-Carrier-to-decoder terminal arming. Common Process-v2 plus the
additional P3.18/P3.19 adapter/registration/arming regressions pass 167/167.

This unit creates a review-pending H0 capability only. It creates no approval,
no prepared live run, no consumed-candidate claim, and no D0, D1, F1,
recovery, replay, or unattended authority. Independent changed-closure review
is required before the manifest may be presented for a fresh attended F1
approval.
