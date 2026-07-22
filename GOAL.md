# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: R4W1-D DIRECT PID1 PROVEN; P2.31 FIRST E1 PROCFS CHECKPOINT
TECHNICALLY PROVEN; P2.34 CANDIDATE ARTIFACT CLOSURE PASS; P2.35 CONNECTED
D0 PREPARED; F1 INACTIVE.**

R4W1-D proved successful `kernel_execve("/init")` while `current` was PID 1.
P2.29 later transferred one exact P2.26 boot-only candidate and one exact
Magisk rollback, then verified final health. Its clean-baseline retained result
contained two exact USERSPACE records and no ENTRY, UNSAT, foreign, malformed,
or partial record. The operator confirmed that the first physical Download
attempt was missed and the candidate booted twice; the source permits one
USERSPACE replacement per boot.

P2.29's immutable exact-one contract correctly rejected two records as
`AMBIGUOUS_INTEGRITY_FAILURE`, so its durable verdict remains
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`. P2.31 binds the exact candidate,
control flow, request ABI, kernel writer, and P2.30 replay. It establishes that
PID 1 mounted procfs, verified `PROC_SUPER_MAGIC`, and caused the kernel to
store the exact first E1 request. It does not prove that write returned or any
later E1 stage.

P2.30 adds an opt-in multiboot evidence policy without changing P2.29. P2.32
now fixes a 45-byte shared-header plus compact A/B latest-stage record, strict
E1A/E1B transitions, torn-update fallback, and multiboot decoding in an
executable H0 model. No implementation, candidate, approval, or live authority
was created by P2.32. P2.33 now implements the default-disabled kernel source,
E1A/E1B userspace, decoder, typed evidence path, and static checker. It creates
no build or candidate, and its offline verifier deliberately refuses promotion.
P2.34 derives one private candidate identity, completes two clean reproducible
Full-LTO builds, independently closes one deterministic boot-only AP, and
promotes the exact three-payload offline evidence contract. It creates no ready
manifest or device binding. The first P2.35 preparation line stopped after two
host-only manifest rejections without device contact. The second rejection
exposed a two-field binary identity versus path-bearing pinned-receipt mismatch;
the bounded adapter fix, actual-bundle H0 replay, 124-test superset, and
independent review passed. That stopped line and its private manifests remain
closed. The next connected D0 initially rejected two exact legacy P2.29
USERSPACE records in the retained baseline. One bounded normal Android reboot
returned healthy and rotated them out; a fresh manifest and run directory then
passed connected D0 and produced one private prepared binding. No active S22+
F1 authorization. The next candidate run requires the fresh exact approval,
one candidate attempt, mandatory rollback, and final health under Process v2.

The controlling next-stage design is
`docs/plans/S22PLUS_FYG8_POST_PID1_OBSERVABLE_RUNTIME_ARCHITECTURE_2026-07-21.md`.

## Established Evidence

- R4W1-A: custom Android `/init` marker retained and rollback passed.
- R4W1-B: a 99-byte ring-crossing marker retained only its 73-byte prefix;
  append-at-cursor evidence is not accepted.
- R4W1-D: one 45-byte contiguous pre-cursor proof, no index mutation, clean
  Full-LTO reproducibility, deterministic construction, live proof, and
  rollback all passed as `PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`.
- P2.21-P2.23: host closure and connected D0 passed; candidate and rollback
  transferred once, final health passed, and observation was `ZERO_AMBIGUOUS`.
- P2.24-P2.25: the current-node 2/2-cell parser defect was isolated and fixed;
  stock-DT premises, clean Full-LTO output, and linked cache-flush PoC passed.
- P2.26-P2.29: deterministic boot-only AP, independent closure, typed evidence,
  connected D0, one candidate transfer, one rollback, and final health passed.
  Two exact USERSPACE records are technically positive but formally no-proof
  under the immutable exact-one contract.
- P2.30: a separate fixed multiboot policy, strict baseline dispatch, archived
  P2.29 replay, focused tests, and independent safety review passed H0.
- P2.31: exact artifact/transfer, request ABI, userspace control flow, kernel
  gate, and raw replay close the first procfs checkpoint semantics H0.
- P2.32: compact 45-byte A/B layout, strict E1A/E1B stage model, torn fallback,
  and fail-closed multiboot policy passed H0.
- P2.33: kernel/client/runtime/decoder source closure, 90,114 adjacent A/B
  variants, static AArch64 links, review, and Process v2 refusal passed H0.
- P2.34: two clean Full-LTO builds, byte-identical kernel artifacts,
  deterministic boot-only packaging, linked audit, exact offline Process v2
  binding, and independent review passed H0.
- P2.35 prep fix: two pre-device manifest rejections stopped the first line;
  the receipt-shape adapter defect was fixed and independently validated H0.
  No D0 command, device action, journal, binding, or approval occurred.
- P2.35 connected D0: the first baseline read stopped on known legacy evidence;
  one normal reboot restored a clean retained baseline, and a fresh D0 run
  bound one healthy target, exact artifacts, and the current execution closure.
  F1 remains inactive and no transaction or transfer attempt exists.
- Process v2: common D0/F1 execution, journal, regular-path Odin transport,
  rollback, and final health are proven.
- V3439: pstore, pmsg, ramoops, and DTBO-based retention remain retired.
- Stock FYG8 proves the USB stack under Android only. Bare-PID1 bind remains the
  largest functional unknown.

Load-bearing details are in:

- `docs/reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md`
- `docs/reports/S22PLUS_FYG8_P223_F1_LIVE_NO_PROOF_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P224_GUARD_ROOT_CAUSE_H0_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P225_GUARD_POC_FLUSH_HOST_PASS_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P226_P228_LIVE_READY_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P229_F1_LIVE_DUPLICATE_USERSPACE_NO_PROOF_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P230_MULTIBOOT_EVIDENCE_POLICY_HOST_PASS_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P231_E1_PROC_MOUNTED_SEMANTIC_CLOSURE_2026-07-22.md`
- `docs/plans/S22PLUS_FYG8_P2_32_E1_LATEST_STAGE_DESIGN_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P233_E1_SOURCE_IMPLEMENTATION_HOST_PASS_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P234_CANDIDATE_ARTIFACT_CLOSURE_HOST_PASS_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P235_PREPARATION_ADAPTER_FIX_HOST_PASS_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P235_CONNECTED_D0_PREPARED_PASS_2026-07-23.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`
- `docs/module-map/s22plus-fyg8/`

Archived text is evidence only; clauses under `docs/archive/` and earlier
reports grant no device authority.

## Immediate Roadmap

1. **P2.1-P2.16 complete/closed:** Process v2, direct PID1 proof, earlier
   experiments, rollback, and health evidence are preserved; bindings consumed.
2. **P2.17-P2.20 complete, H0:** exact snapshot model, bounded same-ring
   discriminator, implementation, and independent review passed.
3. **P2.21-P2.23 complete/closed:** first same-ring F1 closed healthy with
   `ZERO_AMBIGUOUS` observation.
4. **P2.24-P2.25 complete, H0:** parser root cause, exact fix, direct-map
   premises, Full-LTO build, and linked cache-flush audit passed.
5. **P2.26 complete, H0:** deterministic boot-only AP and independent kernel,
   ramdisk, `/init`, child, AP, and writer-exclusion closure passed.
6. **P2.27 complete, H0:** typed Process v2 offline evidence promotion passed.
7. **P2.28 complete, D0:** exact target, health, clean baseline, and prepared
   binding passed without a device write or Odin invocation.
8. **P2.29 complete/closed, F1:** candidate and rollback transferred once;
   final health passed; exact-one formal verdict remains no-proof despite the
   operator-confirmed two-boot USERSPACE callback evidence.
9. **P2.30 complete, H0:** opt-in one-or-more USERSPACE policy, strict clean
   baseline, fail-closed matrix, archived replay, and review passed.
10. **P2.31 complete, H0:** first procfs checkpoint semantics closed.
11. **P2.32 complete, H0:** compact E1A/E1B A/B model and tests passed.
12. **P2.33 complete, H0:** source closure passed; no build or candidate.
13. **P2.34 complete, H0:** two clean reproducible Full-LTO builds, boot-only
    AP, independent artifact closure, and offline Process v2 binding passed.
14. **P2.35 prepared, D0:** exact target, health, clean baseline, artifacts,
    recovery, ordinary paths, and execution closure are bound privately. F1 is
    inactive until the operator supplies the fresh exact approval token.
15. **P2.36 next, F1 after approval:** one candidate attempt, mandatory exact
    rollback, bounded observation, final health, and canonical journal.
16. **E2-E4 later:** prove platform bind and UDC, then one ACM banner and nonce
    exchange. No shell, NCM, Debian, or hot reload.

Do not reactivate R4W1-C3, fork a per-candidate helper, reuse a consumed
approval, load `sec_log_buf.ko` in a checkpoint-bearing native candidate, or
infer bind from module registration.

## Process

For each bounded unit: STATE, SELECT, DESIGN, IMPLEMENT, STATIC VALIDATE,
DEVICE only when required and authorized, REPORT, then scoped COMMIT.

## Success Conditions

The direct-PID1 and first procfs checkpoint are evidenced. The remaining
post-PID1 frontier closes only through separate Process v2 rungs that prove:

- mounts/readbacks plus one exact static child token, exit, and reap;
- watchdog and USB module results separately from platform bind and UDC;
- exact device-to-host ACM bytes; then
- one bounded host request and nonce-bound response.

Every live rung requires exact boot-only identity, bounded evidence, exact
Magisk rollback, final Android/root/supporting-partition health, and a complete
journal. No later rung may infer an earlier unproved result.

## Stop Conditions

- A permanent boundary in `AGENTS.md` would need to change.
- Recovery, rollback, target identity, or Odin endpoint is unavailable.
- An unexplained device-session failure or repeated material failure occurs.
- Three consecutive units add only policy or review with no tested behavior.
- Scope grows to shell, NCM, Debian, or a supervisor before E4 closes.
