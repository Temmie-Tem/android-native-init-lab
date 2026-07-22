# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: R4W1-D DIRECT PID1 PROVEN AND ROLLED BACK; R4W1-E0 F1 CLOSED NO PROOF.** Process v2 transferred
the exact boot-only candidate once, two complete post-rollback
`/proc/last_kmsg` reads retained one exact contiguous proof, the exact Magisk
boot rollback completed, and final Android/root/supporting-partition health
passed. Durable verdict:
`PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`.

The proof is kernel-side. It establishes successful `kernel_execve("/init")`
while `current` was PID 1; it does not establish userspace `_start`, mounts,
module load, child execution, driver bind, USB, or a control loop.

No active S22+ F1 authorization. Any new candidate requires new data, connected
D0 and preparation, fresh exact approval, one candidate attempt, mandatory
rollback, and final health under Process v2.

R4W1-E0 reused R4W1-D's proven 45-byte slot to distinguish post-exec ENTRY from
the first PID1 proc checkpoint. Its clean baseline and D0 passed, then the exact
candidate and Magisk rollback each transferred once. Final Android/root health
passed, but two complete byte-identical retained reads contained zero ENTRY,
USERSPACE, or family bytes. Durable verdict:
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`. The binding is consumed and cannot be
reused. Candidate boot survival was observed by the operator, but no retained
bytes prove kernel selection, successful exec, or userspace entry.

The controlling next-stage design is
`docs/plans/S22PLUS_FYG8_POST_PID1_OBSERVABLE_RUNTIME_ARCHITECTURE_2026-07-21.md`.

## Established Evidence

- R3C1: source-matched unpatched rebuilt kernel booted FYG8 Android and rolled
  back cleanly.
- R4W1-A: custom Android `/init` marker retained and rollback passed.
- R4W1-B: a 99-byte ring-crossing marker retained only its 73-byte prefix;
  append-at-cursor evidence is not accepted.
- R4W1-D: one 45-byte contiguous pre-cursor proof, no index mutation, clean
  Full-LTO reproducibility, deterministic candidate construction, live proof,
  and rollback all passed.
- Process v2: common D0/F1 execution, journal, regular-path Odin transport,
  exact post-transfer departure handling, rollback, and final health are proven.
- V3439: a correctly bound ramoops/pmsg backend retained zero current-run
  records; pstore, pmsg, ramoops, and DTBO-based retention remain retired.
- O3F and earlier S22+ USB runs retained no internal phase. Their
  no-enumeration result cannot identify module, bind, UDC, or gadget progress.
- Stock FYG8 proves the complete USB stack under Android only. Bare-PID1 bind
  remains the largest functional unknown.

Load-bearing details are in:

- `docs/reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md`
- `docs/reports/S22PLUS_FYG8_R4W1D_CONTIGUOUS_PROOF_HOST_DESIGN_2026-07-21.md`
- `docs/reports/NATIVE_INIT_V3439_S22PLUS_CORRECTED_RAMOOPS_LIVE_NO_PROOF_2026-07-11.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`
- `docs/module-map/s22plus-fyg8/`

Archived text is evidence only; clauses under `docs/archive/` and earlier
reports grant no device authority.

## Immediate Roadmap

1. **P2.1-P2.5 complete:** active-contract cleanup, reusable D0/F1 core,
   connected read-only qualification, R4W1-D live proof, rollback, and health.
2. **P2.6-P2.10 complete:** post-PID1 architecture, E1 runtime and carrier,
   deterministic candidate, exact offline binding, and typed Process v2
   evidence were built and reviewed host-only.
3. **P2.11 F1 closed, no proof:** candidate and rollback transferred once and
   final health passed, but retained E1 carrier count was zero. Binding consumed.
4. **P2.12-P2.14 complete, H0 only:** R4W1-E0 reduced the question to ENTRY vs
   first userspace proc checkpoint, built a byte-identical exact candidate, and
   bound a four-state fail-closed classifier into the unchanged common runner.
   That H0 unit created no ready manifest, device contact, or live authority.
5. **P2.15 complete, D0 only:** the three-field ready-manifest promotion and one
   connected read-only preparation passed with a clean retained baseline and
   strict prepared-record reopen. F1 remains inactive.
6. **P2.16 F1 closed, no proof:** candidate and rollback each transferred once,
   final health passed, and two retained reads were identical, but ENTRY,
   USERSPACE, and family counts were all zero. Binding consumed.
7. **P2.17 complete, H0 only:** exact FYG8 source and a tested model prove that
   valid magic plus `idx >= record_size` is sufficient; full ring saturation is
   not required. No usable independent candidate-selection witness was found
   in the current safety envelope.
8. **P2.18 complete, H0 only:** preserve 45-byte ENTRY/USERSPACE, add one
   candidate-bound 24-byte UNSAT for `24 <= idx < 45`, and keep every smaller,
   invalid, nonselected, or lost result as `ZERO_AMBIGUOUS`; no live authority.
9. **P2.19 complete, H0 only:** implemented the corrected target/layout guard,
   candidate-bound records, artifact closure checker, five-state typed raw-byte
   observer, typed D0 baseline, and minimal runner dispatch. Focused tests pass;
   no candidate or live authority was created.
10. **P2.20 complete, H0 only:** independent Opus review of the execution
    closure found no MUST-FIX; no build, artifact, device, or authority occurred.
11. **P2.21 next, H0 only:** build and independently bind vmlinux, Image, boot
    AP, pinned `/init`, no ring writer, and config; no manifest, D0, F1, transfer.
12. **E2-E4 later:** prove module closure, platform bind and UDC, then one ACM
    banner and nonce exchange. No shell, NCM, Debian, or hot reload.

Do not reactivate R4W1-C3, fork a C4 helper, add another per-candidate policy
block, reuse a consumed approval, load `sec_log_buf.ko` in a checkpoint-bearing
native candidate, or infer bind from module registration.

## Process

For each bounded unit:

1. **STATE:** inspect the current frontier, repository state, and last evidence.
2. **SELECT:** choose the smallest action tier that answers the question.
3. **DESIGN:** state expected evidence, stop conditions, and recovery.
4. **IMPLEMENT:** reuse the common path; do not fork for changed hashes.
5. **STATIC VALIDATE:** run focused tests and artifact checks.
6. **DEVICE:** only when required and authorized under `AGENTS.md`.
7. **REPORT:** structured evidence by default; prose for meaningful change.
8. **COMMIT:** one scoped, validated unit.

## Success Conditions

The direct-PID1 rung is closed. The post-PID1 frontier closes only through
separate Process v2 rungs that prove:

- userspace mounts/readbacks plus one exact static child token, exit, and reap;
- watchdog and USB module results separately from platform bind and UDC;
- exact device-to-host ACM bytes; then
- one exact bounded host request and nonce-bound response.

Every live rung requires exact boot-only candidate identity, bounded evidence,
exact Magisk boot-only rollback, final Android/root/supporting-partition health,
and a complete journal. No later rung may infer an earlier unproved result.

The long-term project succeeds when the same method supports repeatable native
PID 1 bring-up across target profiles without weakening target isolation or the
boot-only recovery boundary.

## Stop Conditions

- Any permanent safety boundary in `AGENTS.md` would need to change.
- Physical recovery is unavailable or rollback cannot be verified.
- Device identity or Odin endpoint is ambiguous.
- An unexplained device-session failure occurs.
- The same material failure occurs twice without new evidence.
- Three consecutive units add only policy, metadata, or review machinery with
  no new tested behavior.
- Scope grows to shell, NCM, Debian, or a general supervisor before E4 closes.
