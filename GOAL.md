# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: R4W1-D DIRECT PID1 PROVEN; P2.37 E1A LOCAL RUNTIME LIVE PASS;
P2.39 E1B MODULE RUNTIME LIVE PASS; P2.41 E2 SOURCE IMPLEMENTATION H0 PASS;
F1 CLOSED HEALTHY.**

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
passed connected D0 and produced one private prepared binding. Its exact F1
approval was accepted, but a measured USBFS arrival race stopped the run before
endpoint identification, candidate attempt, or AP transfer. A bounded
no-payload Odin reboot returned the unchanged Magisk boot, and a separate D0
verified Android, FYG8, root, supporting partitions, clean retained baseline,
and no Odin endpoint. The arrival race is fixed and independently reviewed H0.
The consumed binding names the old execution closure and is not reusable.
P2.37 created a fresh closure and D0 binding after the USBFS-arrival fix. Its
single candidate and rollback transfers completed, and two byte-identical
retained reads contained one exact E1A terminal-success record with no UNSAT,
failure, foreign, malformed, historical, or partial record. Final Android,
FYG8, root, supporting partitions, and Odin absence passed. The transaction is
closed, its binding is consumed, and no active S22+ F1 authorization exists.

P2.38 then completed a focused H0 E1B readiness audit. The current E1B runtime,
five-module dependency order, exact FYG8 vendor-ramdisk bytes, and P2.34
kernel/module ABI are compatible. The modules remain in unchanged stock
`vendor_boot`; they must not be injected into the boot-only AP. The remaining
work is a profile-2 candidate pipeline and independent effective-rootfs audit,
not broader research or a device action. No candidate or authority was created.

P2.39 implemented that profile-2 pipeline while preserving the E1A identity
domain. Two clean Full-LTO builds and two package runs were byte identical. The
independent checker composed the candidate boot ramdisk with the pinned stock
`vendor_boot`, verified the exact five-module closure, and promoted the E1B
terminal `0x3f` offline contract. The common verifier now derives the reachable
slot count per profile: E1A remains 32,769 and E1B is 57,345. The 142-test
focused set and independent review passed. A connected D0 preparation then
stopped read-only because `/proc/last_kmsg` still contains P2.37's valid E1A
terminal-success record. No journal, approval, Odin session, reboot, or device
write occurred. One approved D1 normal reboot and a fresh connected D0 are
required before any E1B F1 approval can be requested.

The operator then confirmed that all pre-F1 preparation, including one bounded
D1 normal reboot, was approved. Exactly one `adb reboot` rotated the historical
E1A record out and returned healthy Android. A fresh manifest and run directory
passed connected D0 with Android/root/boot health, exact supporting partitions,
clean retained baseline, exact candidate and rollback APs, and the current
execution closure. One private prepared binding now exists. No Odin invocation,
Download transition, partition transfer, or F1 authorization occurred. The next
action is one exact E1B F1 approval; the candidate must not run before it.

That exact approval was supplied and consumed. One candidate transfer completed,
the operator observed no boot loop, and the transaction reached `OBSERVED`.
The first recovery inventory check stopped before the physical Download endpoint
was available; it did not retry the candidate. Once the exact endpoint appeared,
the same durable transaction resumed with the preapproved Magisk rollback. Two
byte-identical retained reads contained one exact E1B terminal-success record:
generation 14 had reached `WDT_MODULES_VERIFIED` stage `0x35`, and generation 15
reached E1B success `0x3f`. UNSAT, failure, foreign, malformed, historical,
partial, and fallback counts were zero. Final Android, FYG8, root, boot,
supporting partitions, Odin absence, and all eight timeline events passed. The
state is `CLOSED`, the binding is consumed, and no S22+ F1 authority remains.

The controlling next-stage design is
`docs/plans/S22PLUS_FYG8_POST_PID1_OBSERVABLE_RUNTIME_ARCHITECTURE_2026-07-21.md`.

P2.40 completed the focused E2 H0 audit. The exact 59-module FYG8 closure has
one dependency-valid order that prepends `qcom_hwspinlock` to the proven E1B
five-module foundation and then appends the remaining O3 entries. All 210
constraints pass. Source-matched DWC3 control flow and exact-module ELF
relocations prove that successful `dwc3-msm` probe queues child creation, and
the exact child DT plus built-in dual-role configuration can publish the UDC
without a parent mode or configfs write. The unchanged compact carrier has
capacity for profile 3: 76 stages and 307,201 reachable slot variants. This is
implementation readiness only; direct-PID1 bind and UDC remain live unknowns.

P2.41 now implements that contract without building a live candidate. The
planner, profile-3 kernel/client state machine, static runtime, direct exact-
DTBO parser, and independent effective-rootfs checker pass H0. The runtime
requires the exact module prefix after every insertion, rejects `-EEXIST` and
foreign modules, and observes all eight gates under one 20-second read-only
deadline. All 307,201 E2 variants and the 90,114 E1A/E1B regression domain
pass. Independent review returned GO after two diagnostic/DTBO nits were fixed.
Direct-PID1 module execution, bind, child creation, and UDC remain live unknowns.

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
  Its later approval was consumed by a pre-candidate Download abort.
- P2.35 F1 abort and arrival fix: 11 empty snapshots preceded one expected
  Download-node arrival race. No candidate or rollback AP was transferred. A
  no-payload reboot and fresh D0 returned healthy. The measured observer now
  retries only one exact arrival during arrival polling; focused tests and
  independent review passed. F1 remains inactive.
- P2.37 E1A F1: one exact candidate and rollback transfer completed. One clean
  terminal E1A A/B record proved the local mounts, device-node check, static
  child execution, token verification, and reap path. Final health and all
  canonical timeline events passed; the binding is consumed.
- P2.38 E1B readiness: the runtime contract, exact five-module stock closure,
  15-file symvers identity, full R2 module-CRC closure, vendor-rootfs composition,
  and 93 focused regressions passed H0. Implementation remains; no candidate or
  live authority exists.
- P2.39 E1B F1: profile-2 source and userspace, two clean byte-identical
  Full-LTO builds, deterministic boot-only packaging, effective-rootfs module
  closure, exact offline evidence, 142 tests, and independent review passed.
  The first connected D0 stopped read-only on the historical P2.37 E1A terminal
  record. One approved normal reboot rotated it out; a fresh connected D0 then
  passed. One candidate and rollback transfer completed, one exact terminal E1B
  record proved all five module loads plus `/proc/modules` visibility, and final
  health passed. The transaction and authority are closed.
- P2.40 E2 readiness: the reordered 59-module plan satisfies all 210 metadata
  constraints, the exact source/ELF/DT path reaches child and UDC initialization
  without an E2 write, and profile-3 stage capacity passes H0. No implementation,
  build, candidate, device action, or authority was created.
- P2.41 E2 source implementation: the exact generated plan, profile-3 patch,
  checkpoint client, static runtime, direct 11-entry DTBO parser, shipped
  module bytes, 307,201 E2 variants, 90,114 E1 regressions, 55 focused tests,
  and independent review pass H0. No build, candidate, D0, or authority exists.
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
- `docs/reports/S22PLUS_FYG8_P235_F1_PRE_CANDIDATE_USBFS_ARRIVAL_ABORT_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P237_E1A_F1_LIVE_PASS_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P238_E1B_FOCUSED_READINESS_AUDIT_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P239_E1B_CANDIDATE_H0_PASS_D0_BASELINE_STOP_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P239_CONNECTED_D0_PREPARED_PASS_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P239_E1B_F1_LIVE_PASS_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P240_E2_FOCUSED_READINESS_AUDIT_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P241_E2_SOURCE_IMPLEMENTATION_HOST_PASS_2026-07-23.md`
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
14. **P2.35 closed, pre-candidate F1 abort:** approval was accepted but no AP
    transfer occurred; bounded return and post-abort D0 passed healthy.
15. **P2.36 complete, H0:** exact measured USBFS arrival is bounded without
    weakening ambiguity, replacement, absence, or revalidation gates.
16. **P2.37 complete, F1:** E1A terminal success, exact rollback, final health,
    and the canonical timeline passed; authority is consumed.
17. **P2.38 complete, H0:** E1B runtime, module, ABI, and effective-rootfs
    readiness passed; no build, candidate, device action, or authority occurred.
18. **P2.39 complete/closed, F1:** the profile-2 candidate, exact five-module
    load sequence, `/proc/modules` verification, terminal E1B success, mandatory
    rollback, final health, and canonical timeline passed. The binding and
    approval are consumed.
19. **P2.40 complete, H0:** exact E2 module order, bind/UDC source path,
    bounded gate semantics, and profile-3 capacity passed. No implementation or
    device authority was created.
20. **P2.41 complete, H0:** profile-3 source, exact runtime/module/gate
    semantics, direct DTBO closure, exhaustive records, regressions, and review
    passed. No kernel build, candidate, D0, or authority was created.
21. **P2.42 next, H0:** produce reproducible Full-LTO E2 builds, one
    deterministic boot-only candidate, independent artifact closure, and
    offline Process v2 evidence promotion. Do not contact the device.
22. **E3-E4 later:** after a separate E2 live proof, send one ACM banner and
    then one nonce exchange. No shell, NCM, Debian, or hot reload.

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
