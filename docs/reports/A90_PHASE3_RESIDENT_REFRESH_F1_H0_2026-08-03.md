# A90 Phase 3 resident-refresh F1 H0 closure

Date: 2026-08-03

Status: **H0 PASS / CAPABILITY PASS_GO / LIVE NOT AUTHORIZED**

## Outcome

The A90 resident-install-v2 path now accepts the exact healthy V3406 resident
as the starting native identity while retaining the legacy V2321 start for the
unchanged Phase 2 path.  The new Phase 3 path binds the qualified keyed Debian
network/SSH rootfs, stages it absent-only, transfers the unchanged V3406 boot
candidate at most once, and keeps the canonical V2321 boot rollback ready.

The production loader requires one exact framed version fact, one exact
self-test fact, and one non-conflicting `pstore entries=0` fact.  Phase 3 is
coupled only to the exact V3406 resident start.  The resident manifest builder
rebinds the Phase 3 profile, filesystem label, support closure, pristine
provenance, and current native identity from current evidence rather than
retaining Phase 2 template values.

Both boot artifacts are hard-pinned in the final resident builder:

- candidate: boot only, 66,379,776 bytes,
  `3d3e66535654a62f83c5772caba27624acc160911307190de458154acaefdabb`;
- rollback: boot only, 60,882,944 bytes,
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.

Candidate intent remains durable before dispatch, candidate replay remains
forbidden, and every ambiguous or failed candidate path retains the exact
rollback path.  A successful resident-install-v2 terminal still requires one
exact candidate health result, zero resident reboots, and zero rollback
transfers.

The resident inspection also retains the older Phase 2 A/B receipt under the
legacy `debian_ab_receipt` field.  This is reachable auxiliary ancestry
evidence, not the current Phase 3 rootfs identity: the Phase 3 manifest pins
that exact Phase 2 image and receipt as its deterministic base, while the
Phase 3 materialization receipt independently binds the new clean image,
keyed image, profile, label, service content, and hashes.  The loader rejects
the current keyed image if it equals the ancestral Phase 2 image.  Independent
review classified the mixed-looking inspection names as non-blocking and did
not change the canonical receipt or execution closure.

## Independent review

The subagent review initially withheld PASS_GO and found five defects:

1. Phase 3 profile/support rebinding was missing in the final resident builder.
2. The final builder inherited candidate and rollback bytes from its template
   instead of independently hard-pinning them.
3. starting-health identity used substring matches instead of exact framed
   facts.
4. Phase 3 pristine provenance could retain stale Phase 2 evidence.
5. a single pstore line could contain both `entries=0` and a conflicting later
   value.

All five were fixed and regression-bound.  The canonical review receipt is
`A90_PHASE3_RESIDENT_REFRESH_F1_CLOSURE_INDEPENDENT_REVIEW_2026-08-03.json`,
SHA256
`96c7fb966bb3f8da8d6690328ad62798e9b37992ff1fe4dbf3f9da791b5d5273`.
It records `PASS_GO`, zero unresolved findings, unchanged permanent boundaries,
no device authority, and an exact 25-file execution-critical closure.

This is a capability-wide qualification.  It is not repeated per manifest,
qualification, ordinal, or campaign.  Re-review is required only if the named
closure or its semantics changes, or a new hazard or incident occurs.

## Validation

- primary focused regression: `220/220 PASS`;
- adjacent D1 regression: `28/28 PASS`;
- independent review regression: `322/322 PASS` plus builder `5/5 PASS`;
- touched Python `py_compile`: PASS;
- connected preflight and finalizer audits: `contract_issues=[]`;
- staging and F1 orchestrator source-contract audits: empty;
- `git diff --check`: PASS.

The review contacted no device or network and read no private key contents.
The connected work performed separately was bounded A90 D0 only; it sent no
write, payload, reboot, handoff, or flash.  No F1 action is authorized by this
report.  S22+ and the other attached Samsung target were untouched.
