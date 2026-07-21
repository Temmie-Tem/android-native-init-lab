# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: R4W1-D DIRECT PID1 PROVEN AND ROLLED BACK.** Process v2 transferred
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

Historical clauses are inert evidence only:

- `docs/archive/policy/AGENTS_PRE_PROCESS_V2_2026-07-21.md`
- `docs/archive/roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md`
- `docs/reports/`

Archived text is evidence only and grants no device authority.

## Immediate Roadmap

1. **P2.1-P2.4 complete:** active-contract cleanup, reusable host core, host
   validation, and connected read-only D0 qualification.
2. **P2.5 complete:** Process v2 F1 canary, R4W1-D contiguous witness, exact
   rollback, final health, and post-transfer USBFS departure repair.
3. **P2.6 complete:** post-PID1 architecture review. Three repository reviews
   and one persistent Claude discussion converged on one reusable R4W1-E
   retained carrier and four separate evidence rungs.
4. **P2.7 complete, host-only:** R4W1-E now has an exact retained-region
   geometry, immutable PID1 entry, A/B commit-last slots, unchanged-cursor and
   PID1-only kernel gates, E1-E4 profiles, a host codec/static checker, and 23
   passing adversarial tests. No kernel build, image, device contact, or live
   authority was created.
5. **P2.8 complete, host-only:** the exact E1 static PID1 runtime, child,
   checkpoint client, and independent host contract now cover mount readbacks,
   token/exit/reap, five-module watchdog closure, bounded quiet park, terminal
   publication, exact syscall authority, and byte-exact P2.7 request
   compatibility. Twenty focused adversarial tests and final independent
   review pass. No kernel build, image, device contact, or live authority was
   created.
6. **P2.9 next, host-only:** adapt the existing clean Full-LTO R4W1 build and
   candidate audit path to the exact R4W1-E carrier and E1 sources. Produce one
   clean kernel build and an offline E1 ramdisk/candidate contract with a fresh
   manifest-bound run ID. Do not contact or flash a device in this unit.
7. **E2 later:** generated exact USB closure, per-module result, platform bind,
   DWC3 child, and exact UDC as separate checkpoints.
8. **E3/E4 later:** one exact ACM banner, then one fixed nonce-bound exchange.
   No shell, arbitrary command, NCM, storage, Debian handoff, or hot reload.

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
