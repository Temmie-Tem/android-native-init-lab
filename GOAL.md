# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: R4W1-D DIRECT PID1 PROVEN; P2.29 F1 CLOSED DUPLICATE USERSPACE
NO PROOF; F1 INACTIVE.** R4W1-D transferred the
exact boot-only candidate once, two complete post-rollback `/proc/last_kmsg`
reads retained one exact contiguous proof, the exact Magisk boot rollback
completed, and final health passed. Its durable verdict was
`PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`.

The proof is kernel-side. It establishes successful `kernel_execve("/init")`
while `current` was PID 1; it does not establish userspace `_start`, mounts,
module load, child execution, driver bind, USB, or a control loop.

No active S22+ F1 authorization. Any new candidate requires new data, connected
D0 and preparation, fresh exact approval, one candidate attempt, mandatory
rollback, and final health under Process v2.

P2.21 qualified the corrected kernel-to-AP closure and P2.22 passed its ready
data and D0. P2.23 transferred candidate/rollback once and passed final health,
but two byte-identical reads classified `ZERO_AMBIGUOUS`. Binding consumed.

P2.24 host analysis isolated the first deterministic P2.23 failure: the target
guard used parent-cell `of_address_to_resource()` on a Samsung current-node
2/2-cell `reg` encoding, obtained resource start `0x8`, and rejected the
required `0x800200000` before reading retained magic or index. P2.23 therefore
did not test record storage or cache-to-DRAM persistence.

P2.25 implements the exact current-node parser and linked cache-flush PoC.
P2.26 independently closed one boot-only AP around that exact Image. P2.27
promoted its typed offline evidence, and P2.28 passed connected preparation.
P2.29 transferred candidate and rollback once each and verified final health.
Its clean-baseline retained result contained two exact USERSPACE records in
different warm-reset generations. The immutable exact-one contract therefore
rejected the result as `AMBIGUOUS_INTEGRITY_FAILURE`; the approval is consumed
and no retry is authorized.

The controlling next-stage design is
`docs/plans/S22PLUS_FYG8_POST_PID1_OBSERVABLE_RUNTIME_ARCHITECTURE_2026-07-21.md`.
## Established Evidence

- R4W1-A: custom Android `/init` marker retained and rollback passed.
- R4W1-B: a 99-byte ring-crossing marker retained only its 73-byte prefix;
  append-at-cursor evidence is not accepted.
- R4W1-D: one 45-byte contiguous pre-cursor proof, no index mutation, clean
  Full-LTO reproducibility, deterministic candidate construction, live proof,
  and rollback all passed.
- P2.21-P2.23: host closure and connected D0 passed; candidate and rollback
  transferred once, final health passed, and two identical retained reads were
  `ZERO_AMBIGUOUS`. The F1 binding is consumed.
- P2.25: exact Samsung-style target parsing, stock-DT direct-map premises,
  clean Full-LTO output, and cross-tool linked cache-flush PoC audit pass H0;
  reset retention remains a live unknown.
- P2.26-P2.29: deterministic boot-only AP, independent kernel/rootfs/writer
  closure, typed evidence promotion, connected clean-baseline D0, one exact
  candidate transfer, one exact rollback, and final health all pass. Two exact
  USERSPACE records violate the exact-one live contract, so F1 remains no-proof.
- Process v2: common D0/F1 execution, journal, regular-path Odin transport,
  exact post-transfer departure handling, rollback, and final health are proven.
- V3439: a correctly bound ramoops/pmsg backend retained zero current-run
  records; pstore, pmsg, ramoops, and DTBO-based retention remain retired.
- Stock FYG8 proves the complete USB stack under Android only. Bare-PID1 bind
  remains the largest functional unknown.
Load-bearing details are in:

- `docs/reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md`
- `docs/reports/S22PLUS_FYG8_R4W1D_CONTIGUOUS_PROOF_HOST_DESIGN_2026-07-21.md`
- `docs/reports/S22PLUS_FYG8_P221_ARTIFACT_CLOSURE_HOST_PASS_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P223_F1_LIVE_NO_PROOF_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P224_GUARD_ROOT_CAUSE_H0_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P225_GUARD_POC_FLUSH_HOST_PASS_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P226_P228_LIVE_READY_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P229_F1_LIVE_DUPLICATE_USERSPACE_NO_PROOF_2026-07-22.md`
- `docs/reports/NATIVE_INIT_V3439_S22PLUS_CORRECTED_RAMOOPS_LIVE_NO_PROOF_2026-07-11.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`
- `docs/module-map/s22plus-fyg8/`

Archived text is evidence only; clauses under `docs/archive/` and earlier
reports grant no device authority.

## Immediate Roadmap

1. **P2.1-P2.16 complete/closed:** Process v2, direct PID1 proof, E1/E0
   experiments, rollback, and health evidence are preserved in their reports;
   all earlier F1 bindings are consumed.
2. **P2.17-P2.20 complete, H0:** exact snapshot model, bounded same-ring
   discriminator, implementation, and independent review pass.
3. **P2.21-P2.23 complete/closed:** first same-ring artifact/D0 closure ran once;
   final health passed but observation was `ZERO_AMBIGUOUS`.
4. **P2.24-P2.25 complete, H0:** parser root cause, exact 2/2-cell fix,
   direct-map premises, Full-LTO build, and GNU/LLVM cache-flush PoC audit pass.
5. **P2.26 complete, H0:** one deterministic boot-only AP and independent
   kernel, ramdisk, `/init`, child, AP, and writer-exclusion closure pass.
6. **P2.27 complete, H0:** typed Process v2 offline evidence promotion passes.
7. **P2.28 complete, D0:** connected exact-target, health, clean-baseline, and
   prepared-binding checks passed with no device write or Odin invocation.
8. **P2.29 complete/closed, F1:** candidate and rollback transferred once and
   final health passed. Two exact USERSPACE records in distinct warm-reset
   contexts violated the immutable exact-one contract; verdict is no-proof.
9. **P2.30 next, H0:** model recovery-induced multi-boot cardinality and design
   a bounded positive rule without changing the archived P2.29 verdict.
10. **E2-E4 later:** prove module closure, platform bind and UDC, then one ACM
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
