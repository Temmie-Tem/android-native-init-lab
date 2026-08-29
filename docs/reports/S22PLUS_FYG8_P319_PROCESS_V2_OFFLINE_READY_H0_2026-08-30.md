# S22+ FYG8 P3.19 Process-v2 offline-ready H0 closure

Date: 2026-08-30 KST

Status: `PASS_GO_P319_PROCESS_V2_OFFLINE_READY_CENSUS_DECOUPLE_H0_CAPABILITY_V1`

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
- prerequisite receipt `-12-p319-census-decoupled`: 13,190 bytes / `4a18cf1148a7c8bd…`,
  mode 0400, link count one.
- Integration V2 `-16`: 126,135 bytes / `1506e8988dfe2c9…`, mode 0400,
  link count one, zero blockers, `SOURCE_CLOSURE_PASS_RUNTIME_CLASSIFICATION_PENDING`.
- candidate-static `-11`: 35,309 bytes / `d00f422e46c55c15…`, mode 0400,
  link count one.
- promotion `-11`: `candidate-static.json` `35309B/d00f422e…`,
  `run-manifest.json` `1043B/172a873a…`, and
  `static-check-result.json` `1842B/08a25d61…`; all are direct
  mode-0400, link-count-one files.
- tracked ready manifest: 2,432 bytes / `e6c758460f45e52b…`, direct regular
  link-count-one mode 0644 or Git-umask-equivalent 0664, schema
  `device_action_f1_candidate_v2`, status
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

Post-review host validation exposed one cross-target coupling that the clean
review worktree could not show. Five unrelated A90 revalidation files changed
the diagnostic raw-first census from 1747/412 to 1752/415 while the approved
semantic projection remained `5b1f42dd…`. The prerequisite had correctly used
that projection for safety but then copied the two excluded census integers
back into its exact receipt, making the candidate-static authority fail only
because another target added files. The successor keeps the count-change
positive controls but stores only the semantic projection digest in the
prerequisite authority. It also accepts exactly 0644 or 0664 for the tracked
public declaration because Git records only executable versus non-executable
mode; 0666 and every other mode remain rejected. Private promotion artifacts
remain exact mode 0400. No evidence field or device boundary is relaxed.

Intermediate private raw-first `-19` through `-22`, prerequisite `-04` through `-11`,
Integration `-06` through `-15`, candidate-static `-02` through `-10`, and
promotion `-01` through `-10` artifacts remain preserved as non-authoritative
predecessors. Integration `-11/-12` record the correct fail-closed reaction to
an interim adapter identity drift. The unused host-only requalification
`-12/-56/-57` independently reproduced the same candidate bytes but is not
referenced by the final chain. None grants authority.

## Validation and boundary

The census-decoupled chain covers 69/69 distinct focused checks: prerequisite,
ready/promotion and taxonomy paths, including exact manifest derivation, mode
normalization, semantic-census exclusion, registry absence, hostile provenance,
stale-bytecode, exact types and no-clobber behavior. A main-population validation
with the five unrelated A90 files present returns
`PASS_DEVICE_ACTION_F1_LIVE_V2_HOST_READY`; it proves the 1752/415 diagnostic
census no longer changes the exact chain. The unchanged common Process-v2 plus
P3.18/P3.19 adapter/registration/arming predecessor selection passed 167/167.

Independent read-only review of exact commit `0659738a49` reproduced raw `-23`,
verified its predecessor identity chain, stable-source stale-bytecode control,
current registry absence and matching-claim rejection, and returned `PASS_GO`.
Independent read-only review of exact commit `6d7bd57378` reproduced the
cross-target census control, semantic projection, 0664 acceptance and 0666
rejection, private 0400 chain, final identities, registry 0/0 and H0 boundaries,
then returned `PASS_GO`. This creates no approval, prepared live run,
consumed-candidate claim, or D0, D1, F1, recovery, replay, or unattended
authority. Runtime witnesses remain pending; the manifest may be presented
only for a fresh attended F1 approval.
