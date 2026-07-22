# S22+ FYG8 P2.20 independent safety review host GO

Date: 2026-07-22 KST
Tier: H0, host-only read-only review and documentation
Reviewed commit: `0bdd28a1`
Status: `GO_P220_HOST_CLOSURE`
Live authority: none

## Scope

One independent Claude Opus 4.8 review inspected the execution-critical delta
in `0bdd28a1^..0bdd28a1`: the P2.19 kernel patch, fixed record decoder, contract
checker, typed D0/evidence/F1 dispatch, focused tests, and only the design and
result text needed to check semantic consistency. The reviewer had read-only
repository tools in plan mode. It did not edit, build, create or repack an
artifact, contact a device, invoke Odin, flash, or authorize F1.

Codex then checked every material disposition against the repository and used
the same persistent review conversation for one focused correction round.

## Verdict

`GO_P220_HOST_CLOSURE`

There is no MUST-FIX in the reviewed host closure. Exact USERSPACE remains the
only accepted state. ENTRY and UNSAT are diagnostic, while zero, mixed,
duplicate, foreign, malformed, or edge-partial observations fail closed.
Nothing in P2.19 weakens the common Odin, approval, USBFS departure, journal,
rollback, or final-health path.

## Findings And Disposition

### Forward gates for P2.21

1. `verify_extracted_artifact_closure()` checks caller-supplied extracted bytes;
   it does not itself decompress the AP member or unpack boot. This is honest in
   the current result because `candidate_artifacts_verified` remains false and
   no candidate exists. P2.21 must independently derive the AP inventory,
   decompress `boot.img.lz4`, unpack boot, and prove the extracted kernel equals
   the checked Image before any transfer.
2. USERSPACE substitution relies on the frozen Samsung-ring cursor. The kernel
   path fails closed if another writer advances the header, but P2.21 must prove
   the candidate ramdisk contains the pinned static `/init` and does not load
   `sec_log_buf.ko` or any other writer for `0x800200000`.
3. The new config is enabled in `gki_defconfig`. P2.21 must verify it is present
   in the S22+ candidate's compiled config and that the resulting artifact is
   scoped only to this target.
4. Cache-to-DRAM persistence remains a later live acceptance property. The
   identical pre-cursor write mechanism is already live-proven by R4W1-D, but
   P2.20 does not turn that prior proof into authority for a new candidate.

These are build, artifact, or later live gates. They do not block beginning the
P2.21 host build and they do not create D0 or F1 authority.

### Source-verified corrections

- The initial review listed `phys_to_virt()` mapping validity as unverifiable.
  The exact FYG8 source audit in
  `s22plus_fyg8_r4w1_patch_check.py:251-304` checks all eleven g0q DT revisions,
  pins the carveout and log-buffer ranges, checks the memory-region phandle and
  strategy 3, and rejects `no-map`. This closes the direct-map concern for the
  pinned source. The stock DT actually supplied at a later boot remains bound
  by target and connected evidence, not inferred from this review.
- ENTRY or UNSAT bytes are stored before the post-write header check. If that
  check fails, a diagnostic record can remain while userspace arming stays
  disabled. This does not overclaim: path, PID 1, initial valid magic, index
  threshold, and the pre-write stable-header check all precede the store. The
  records claim only post-exec hook reach and, for UNSAT, the sampled index
  range. Only a post-check-armed exact USERSPACE replacement can be accepted.
- The decoder combines head- and tail-edge partials into one integrity flag.
  This loses diagnostic direction only; either edge still fails closed.

## Verified Properties

- target, model, DT compatible, strategy, physical base, and size are checked
  before resolving the direct-mapped ring pointer;
- writes are bounded to 24 or 45 payload bytes and never mutate magic, index,
  previous index, or boot count;
- candidate records derive from a fixed, non-self-referential contract preimage
  and acceptance identity is not manifest-selectable;
- compiled-blob cardinality rejects retired E0 records and unexpected family
  copies;
- typed D0 baseline rejects either family and recognizable edge fragments;
- the Process v2 execution-source closure pins the new decoder and static
  checker without changing transport or recovery behavior; and
- all P2.19 safety flags remain host-only with candidate artifact verification
  false.

## Review Session

Persistent conversation: `99d22938-a036-4497-8aba-d1f294c03d7f`

Both rounds used Claude Opus 4.8, standard speed, fast mode off. Combined direct
CLI measurements were approximately 748.7 seconds wall time, 49,551 output
tokens, 1,380,891 cache-read tokens, 443,532 cache-creation tokens, and
USD 6.3647. Subscription-window percentages were not recorded. The second
round resumed the same conversation; session persistence was enabled.

## Boundary

P2.20 closes only the independent host review required by `AGENTS.md`. No
kernel was compiled, no candidate or manifest was created, no device was read
or controlled, and no live action is authorized. P2.21 is a separate H0 build
and independently re-derived artifact-closure unit.
