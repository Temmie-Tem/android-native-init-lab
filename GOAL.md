# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: direct PID1, E1A/E1B, E2 through the real UDC, and E3 through exact
configfs UDC binding are live proven. P2.84 F1 is closed after one candidate
and one exact rollback transfer. Retained `0x8e/detail=0` proves corrected
NONE readback and `dwc3_otg_start_peripheral(off)` return, not outer
`dwc3_otg_sm_work` quiescence. `0x8f/detail=0xc18` proves controlled child
suspend plus a zero-return power-off helper, not electrical rail change.
Focused H0 analysis finds the immediate DEVICE write can block flushing that
outer work and the nominal helper timeout then blocks in `wait4`; this exactly
fits the no-`0x90` shape but neither identifies the parent-suspend wedge nor
repairs it with a fence. The power call is nested in child suspend before the
later parent suspend, so it cannot be moved after outer return by a PID1 fence.
Exact rollback and final health passed. Exact source also rules out a
same-queue `perf_vote_work` self-deadlock. The next discriminator is the
refined, fresh-approved stock D1; connected D0 found no TCP-ADB transport and
no S22+ live run is currently authorized.**

P2.69 derived the fresh v4 intent, completed two clean Full-LTO builds in
`40:43.23` and `40:45.31` with no swap, and proved byte equality for all six
linked artifacts. The P2.60 linked audit, two deterministic boot-only package
runs, independent static closure, and offline Process v2 promotion pass.
Before D0, a downstream host-contract audit found that promotion and
acceptance inherited legacy E2 terminal `0x8f` instead of P2.60 terminal
`0x90`. Kernel, `/init`, package, and AP bytes were unaffected. The invalid
host outputs were quarantined; one version-aware selector now serves both
consumers, legacy E2 remains `0x8f`, P2.60 requires `0x90`, and a stale
P2.60 `0x8f` acceptance is rejected. The same candidate AP was re-promoted
and its host-ready bundle validates. No device contact or live authority
exists. Exact generic-arm64 QEMU execution then invalidated the candidate
before D0: configfs resolves the supplied symlink target from PID1's `/`
working directory, so `../../functions/acm.usb0` fails with `ENOENT`. A
diagnostic absolute creation target succeeded, but configfs canonicalized the
readback as `../../../../usb_gadget/g1/functions/acm.usb0`, which the candidate
also rejected. The frozen P2.69 AP and bundle were not modified and are
retired from live use.

P2.70 separates the absolute configfs creation target from the canonical
readback target and binds both values into the versioned source contract.
A bounded generic-arm64 QEMU harness boots an official Debian arm64 kernel,
loads configfs/libcomposite/dummy-hcd/ACM modules, includes the exact P2.60
runtime, and adapts only the Qualcomm role/UDC boundary. Exact execution passes
stages `0x88..0x8f`, including pre-bind `ttyGS0` queuing and exact 49-byte
receipt through `ttyACM0`. The corrected runtime source, fresh intent,
two-link userspace build, focused tests, and historical host regression suite
pass. QEMU does not prove Qualcomm DWC3-MSM, PHY, Type-C/VBUS, Samsung
notifiers, or physical enumeration.

P2.71 found that the independent stock-closure checker treated incidental ELF
slash strings as mandatory authority. The current linked `/init` correctly
omitted `"/8@"`, so an otherwise reproducible first pair was retired before
D0. Required runtime paths and optional ELF artifacts are now separate;
required omission and unregistered addition still fail. A fresh source-bound
intent and userspace rehearsal pass. Clean Full-LTO A/B complete in
`39:30.23` and `38:20.13`, use no swap, peak at `69.5 C` on the documented
default throttle lane, and match across all six linked artifacts. The
versioned GNU linked audit, deterministic boot-only package pair, independent
effective-rootfs closure, and offline Process v2 promotion pass. No ready
manifest, D0, approval, or device action occurred.

P2.72 binds that exact promoted AP, the target profile's exact Magisk rollback,
the three offline evidence contracts, E2 terminal `0x90`, the versioned P2.60
source closure, and its source-derived CDC-ACM observer into one data-only
ready manifest. The unchanged common runner reopens the complete bundle and
returns `PASS_DEVICE_ACTION_F1_V2_HOST_PREFLIGHT`; a separate regression test
pins the exact bundle and all no-live-authority flags. An initial host-only
draft with historical runner `host-core-1` was rejected and corrected to the
current `host-core-3` before acceptance. No D0, approval, Odin session, device
contact, transfer, reboot, or write occurred.

P2.73 freezes every manifest-bound and live execution-critical source through
the next attended transaction. The unchanged live adapter reopens the exact
bundle and renders the D0/approval/execute/recover sequence with all authority
flags false. Two prior post-rollback deviations are strongly localized to a
Download-to-Android USBFS baseline-inventory race before any snapshot receipt;
the exact inner exception remains unrecorded. Do not patch the bound runner
now. If the same exact error recurs after durable `ROLLBACK_FLASHED`, resume
the same journal with `--recover`; never repeat candidate or rollback.

P2.74 adds a bounded host-only sidecar for the attended F1 window. It records
kernel USB messages, USB/TTY udev events, and start/end `lsusb` snapshots from
before `--execute` through rollback, optional same-run recovery, and final
health. It never opens candidate ACM, is not an acceptance gate, writes only
private evidence, and marks raw public export forbidden. The P2.72 bundle and
execution-closure hashes are unchanged.

P2.75 adversarially reviews approval binding, archive/Odin pinning, target and
Download continuity, CDC-ACM ownership, retained acceptance, journal resume,
rollback, final health, and sidecar behavior. It restores the active-contract
line-count test without weakening its limit and corrects the P2.73 rehearsal's
incomplete recovery-state description. The full FYG8 stock ZIP matches policy,
all historical journals are terminal, and the frozen bundle/closure still
validate. Connected D0 and fresh exact approval remain separate.

P2.76 then used the exact ready2 manifest once. The host observer ran for the
full 180-second bound and found no candidate endpoint. Two byte-identical
retained reads preserve generation 87 progress at UDC-bind stage `0x8e`,
followed by generation 88 failure at configured-state stage `0x8f` with
`ETIMEDOUT`. The operator observed a successful candidate boot and no boot
loop. One exact rollback restored Android, FYG8 kernel, root, boot, and
supporting-partition health; the durable verdict is
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`. The P2.74 diagnostic sidecar was not
running, so this run has no independent host connect/reset trace.

P2.77 H0 reconstructs the combined retained buffer and the exact FYG8 source
path. Candidate kernel printk is absent: ABL reports no `KlogOffset` before the
checkpoint, while matching USB and Max77705 strings elsewhere are stale
Android or bootloader data. Exact extraction of the 60 selected vendor
modules finds no firmware metadata or undefined firmware-request API, and the
Max77705 firmware-bearing modules are not selected. In the exact driver,
`mode_store()` queues the DWC3-MSM state machine and returns before it
completes; mode readback and pre-existing UDC membership are not completion
fences. Stage `0x8e` does prove configfs bind and a synchronous DWC3 pull-up
request returned success. That analysis selected P2.80 to preserve the last
UDC state and speed, classify bounded DWC3 progress, and run the host USB
sidecar before changing modules, firmware, or gadget composition.

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
- P2.42 E2 F1: one exact candidate and rollback transfer completed. One clean
  terminal E2 failure record proves all 59 exact module loads and prefix
  verifications plus `hwspinlock`, `smem`, and `cmd-db` binds. The `rpmh`
  bind predicate timed out at stage `0x7e` with detail 110. Final health and
  the canonical timeline passed; the transaction and authority are closed.
- P2.43 RPMh dependency H0: exact source, config, DTB/DTBO, boot arguments,
  module plan, and metadata prove the display/apps RSC split, built-in PSCI
  provider path, strict pre-probe supplier semantics, and one 12-gate
  replacement contract. Replacement live state remains unknown.
- P2.44 E2 provider implementation H0: exact historical sources produce one
  pinned 12-gate plan/runtime/checkpoint/kernel-patch closure; 59 modules,
  210 constraints, static linkage, vendor-rootfs bytes, expanded record
  exhaustiveness, and E1 regressions pass. Replacement live state remains
  unknown.
- P2.45 E2 candidate H0: the explicit provider source contract, versioned
  80-stage decoder, two clean Full-LTO builds, six byte-identical build
  artifacts, two byte-identical boot-only packages, exact 59-module rootfs
  closure, linked flush audit, and Process v2 offline promotion pass. No
  device authority exists.
- P2.46 E2 F1: after one baseline rotation and clean connected D0, one exact
  candidate and rollback transfer completed. One clean progress record proves
  all 59 modules and gates through `apps-rpmh-mxlvl` at `0x82`. A stale kernel
  item-index range makes every normal `0x83,item=8` checkpoint unrecordable;
  the live record does not prove that request was submitted. Terminal E2
  remains unproven. Final health and the canonical timeline passed; the
  transaction and authority are closed.
- P2.47 gate-range focused audit H0: all 12-gate layers except the kernel
  request validator agree through `0x86`; the final reproducible `vmlinux`
  implements the stale offset comparison against eight. Existing tests and
  linked checks miss it, and prior-gate regression is separately unrecordable.
  No build, image, candidate, device action, or authority was created.
- P2.48-P2.49 derived-validator closure: one descriptor now drives the
  80-stage contract. Two clean Full-LTO builds, linked semantic audits,
  deterministic boot-only packaging, offline closure, baseline rotation, and
  a fresh connected D0 pass produced the private binding consumed by P2.50.
- P2.50 E2 F1: one exact candidate and rollback transfer completed. The
  corrected validator records `gcc-waipio` success at `0x83`, then `ssusb`
  timeout at `0x84`. Final health and timeline passed; authority is consumed.
- P2.58A passed terminal stage `0x8f` after exact UDC target membership at
  `0x87`; one exact record was accepted, and exact rollback, final health, and
  the canonical timeline passed. Authority is consumed.
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
- `docs/reports/S22PLUS_FYG8_P242_E2_CANDIDATE_H0_PASS_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P242_E2_F1_LIVE_RPMH_TIMEOUT_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P243_RPMH_DEPENDENCY_AUDIT_H0_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P244_E2_PROVIDER_IMPLEMENTATION_H0_2026-07-23.md`
- `docs/reports/S22PLUS_FYG8_P246_E2_PROVIDER_F1_LIVE_PROGRESS_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P247_GATE_RANGE_FOCUSED_AUDIT_H0_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P248_DERIVED_VALIDATOR_IMPLEMENTATION_H0_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P249_DERIVED_VALIDATOR_CANDIDATE_D0_READY_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P250_E2_F1_GCC_PASS_SSUSB_TIMEOUT_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P251_SSUSB_DEPENDENCY_AUDIT_H0_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P251B_PHY_NESTED_CLOSURE_H0_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P252_SSUSB_TIMEOUT_CLASSIFIER_DESIGN_H0_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P254_PROOF_BOUND_SSUSB_CLASSIFIER_CANDIDATE_H0_PASS_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P255_REACHABLE_CONTRACT_VERIFIER_FIX_H0_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P255_CONNECTED_D0_PREPARED_PASS_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P255_F1_LIVE_QNOC_MC_VIRT_ABSENT_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P256_QNOC_MC_VIRT_AND_ODIN_OBSERVER_H0_2026-07-24.md`
- `docs/reports/S22PLUS_FYG8_P258A_F1_LIVE_TERMINAL_UDC_PASS_2026-07-25.md`
- `docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`
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
21. **P2.42 complete/closed, F1:** two clean reproducible Full-LTO builds, two
    byte-identical package runs, one deterministic boot-only E2 candidate,
    independent AP/rootfs closure, bounded modern and Samsung legacy LZ4
    decoding, and offline Process v2 promotion passed. One approved D1 baseline
    rotation and fresh connected D0 passed. The exact F1 then proved 59 module
    operations and the first three bind gates before `rpmh` timed out at stage
    `0x7e`; exact rollback and final health passed. The binding is consumed.
22. **P2.43 complete, H0:** the exact display/apps RSC split, PSCI provider,
    strict pre-probe supplier behavior, omitted display-clock explanation, and
    bounded no-module-growth replacement chain pass. P2.42 runtime supplier
    state remains unobserved; no candidate or live authority was created.
23. **P2.44 complete, H0:** one SHA-pinned transformation implements the
    six-predicate PSCI/apps-RSC/RPMh-provider/GCC replacement, 12 total gates
    (`0x7b..0x86`), terminal `0x8f`, and the expanded profile-3 transition
    model. Generated-source, linked-runtime, vendor-rootfs, focused, and
    regression checks pass. No build, candidate, device action, or authority.
24. **P2.45 complete, H0:** the verified P2.44 outputs are bound by one
    versioned source contract and decoder; two clean reproducible Full-LTO
    builds, two deterministic boot-only packages, effective-rootfs closure,
    linked audit, independent review, and Process v2 offline promotion pass.
25. **P2.46 complete/closed, F1:** one exact candidate and rollback transfer
    completed. The provider correction passed through `apps-rpmh-mxlvl` at
    `0x82`; the stale kernel item-index range makes the next normal checkpoint
    unrecordable, while the live result does not prove that it was submitted.
    Final health passed and authority is consumed.
26. **P2.47 complete, H0:** the stale kernel item-range and final Full-LTO
    compare against eight are proven; all other 12-gate layers agree, existing
    coverage misses the mismatch, and the prior-gate regression path has a
    separate no-record gap. No candidate or authority was created.
27. **P2.48 complete, H0:** the versioned adapter derives stage/item semantics
    from one descriptor, records prior-gate regression at the monotonic
    frontier, pins all delegated sources and the selector, and adds fail-closed
    source, mutation, and linked-validator checks. Historical bytes are
    unchanged; no kernel or candidate was built.
28. **P2.49 complete, H0+D0:** after one host-only compile catch, two corrected
    clean Full-LTO builds, linked-validator audits, deterministic boot-only
    packages, independent closure, and offline promotion passed. One baseline
    rotation and fresh connected D0 passed; a private binding awaits exact F1
    approval.
29. **P2.50 complete/closed, F1:** one exact candidate and rollback transfer
    completed. The E2 record proves `gcc-waipio` at `0x83` and records
    `ssusb` timeout at `0x84`; final health and timeline passed. The binding
    and authority are consumed.
30. **P2.51 complete, H0:** exact source, four vendor DTBs, same-build stock
    topology, shipped-module relocations, P2.49 runtime, and the P2.50 record
    narrow `a600000.ssusb` to pre-probe supplier wait, probe-time GDSC/PHY,
    internal probe failure, or shared-deadline late bind. Missing module, GCC,
    redriver, and fatal in-probe ICC-get explanations are ruled out. The
    20-second deadline is shared across all gates, so SSUSB had an unknown
    `0..20` second dwell.
31. **P2.51b complete, H0:** all four vendor DTBs have the same nested
    HS/SS-PHY closure: five RPMh LDO wrappers plus Waipio TLMM, with GCC and
    RPMh clocks/resets already upstream. Exact packaged module bytes and every
    recursive hard dependency are in the existing 59-module plan. GDSC has no
    external supplier, and exact PHY ELF lacks both sysfs imports required by
    the matched source's tuning branch. The SS failed-probe cleanup asymmetry
    is a conditional later lead, not a live result. No module or stage growth
    is justified.
32. **P2.52 implementation complete, H0:** one versioned descriptor now
    generates 15 ordered exact bind checks, the userspace and kernel exact
    detail whitelists, decoder semantics, linked-table expectations, and
    mutation tests. Only details `0xa01..0xa0d`, `0xa20..0xa21`, `0xa10`, and
    `0xa30` are added at stage `0x84`/item 9; all other reserved values remain
    rejected. The parent/prior-gate finalizer, strict waiting parser,
    non-resetting five-second grace, exit rescan, and checked zero-wait
    downstream drain passed focused tests.
    P2.48 generation and the 80-step/59-module plan remain unchanged; the
    kernel patch applies cleanly and two static AArch64 links are byte-identical.
    No kernel, image, candidate, connected read, or device action occurred.
33. **P2.53 complete, H0 proof-gap catch:** the first final linked adapter did
    not prove validator dominance over all retained writes, and the first
    stock-rootfs adapter did not isolate historical module state. Qualification
    stopped host-only; no P2.53 candidate was promoted.
34. **P2.54 complete, H0:** one new source contract binds CFG-aware linked
    validation, isolated stock closure, dispatch, and candidate enforcement.
    Two canonical-path clean Full-LTO builds have six byte-identical artifacts.
    Exact retained-write dominance, deterministic boot-only packaging,
    effective 59-module rootfs closure, independent checking, and Process v2
    offline promotion pass. Historical routing remains unchanged; the moving
    selector registry means tests prove behavior, not immutable old selector
    receipts. No device authority exists.
35. **P2.55 H0 and connected D0 complete:** the Process v2 evidence verifier
    now derives versioned reachable-record shape and values from the selected
    source contract instead of the pre-P2.52 fixed key set. Historical
    no-source-contract shape, strict type checks, focused/legacy regressions,
    independent review, and exact P2.54 host-ready validation pass. After one
    historical-baseline stop and one bounded normal reboot, a fresh D0 passed
    exact health, rollback, candidate, clean baseline, Odin absence, and the
    current closure. One private prepared binding exists and reopens cleanly.
    It has no transaction and grants no F1 authority.
36. **P2.55 complete/closed, F1:** one exact candidate and rollback transfer
    completed. Two byte-identical retained reads contain one exact failure:
    generation 76 passed `0x83`; generation 77 failed stage `0x84`, item 9
    with classifier detail `0xa04`, `qnoc-mc-virt-bind-absent`. Final health
    and all eight timeline events passed after journal-based recovery from a
    post-rollback USB measurement error. The formal verdict is no-proof
    because terminal success was not observed. Binding and approval are
    consumed.
37. **P2.56 complete, H0:** all four exact DTBs and the extracted shipped ELF
    files make mc_virt consume apps and display BCM voters. The exact source
    and ELF return `-EPROBE_DEFER` when an enabled voter is absent, and the
    display voter is populated only after the display RSC probes. The plan
    omits its stock `dispcc-waipio.ko` supplier while containing all four hard
    module dependencies. This is the leading strong static hypothesis for
    `0xa04`, not a live root-cause proof; `PART_DISPLAY`, intermediate binds,
    and the qnoc return code remain unobserved. Exact USBFS receipt replay also
    reproduces the generic post-rollback observer error and identifies the
    missing durable inner exception.
38. **P2.57 pivot, Unit B, Unit A, and candidate qualification complete,
    H0+D0:**
    connected stock D0 returned `DISPLAY_ENABLED_VERIFIED` with exact `0`/`0`
    source values and healthy Android, so Unit A was eligible. The exact
    `s22plus-fyg8-p257-e2-qnoc-display-closure-v1` contract inserts only the
    pinned stock `dispcc-waipio.ko`, derives 60 modules/81 steps, and adds
    display-clock/RSC/voter classifier coordinates before mc_virt. Generation,
    patch/link, stock closure, exhaustive record, historical SHA, reserved
    detail, and stale 59-module/80-step/generation-80 rejection checks pass.
    Source review corrected an MMIO-only assumption: probe performs transient
    standard regulator and ICC votes, with proxy/error-path state potentially
    retained until sync-state or reboot, but has no persistent-storage, fuse,
    bootloader, partition, or raw PMIC write path. Unit B remains unchanged.
    Restricted independent re-review returned GO with no finding. Two clean
    Full-LTO builds, deterministic package runs, linked/independent closure,
    Process v2 offline promotion, host-ready validation, and connected D0
    passed.
39. **P2.57 complete/closed, F1:** one exact candidate and rollback transfer
    completed. Generation 79 passed DWC3 core at `0x86`; generation 80 failed
    the final UDC gate at `0x87`, item 11 with `ETIMEDOUT`. Final health and
    all eight timeline events passed after journal-based recovery from a
    post-rollback USB inventory error. The formal verdict is no-proof because
    terminal success was not observed. Binding and approval are consumed.
40. **P2.58 complete, H0:** P2.57's
    `entries == 1 && exact == 1` UDC predicate conflicts with the compiled and
    stock-observed `dummy_udc.0 + a600000.dwc3` topology. Its timeout cannot
    prove exact-target absence. Exact source separately proves DWC3 bind
    precedes queued role-worker completion, and the shared deadline can reduce
    UDC dwell to one check.
41. **P2.58A implementation and qualification complete, H0:**
    the versioned observation contract now requires
    exact-target membership and symlink identity while permitting unrelated
    UDC peers, and starts one fresh five-second UDC deadline after DWC3 success.
    The canonical stock topology plus seven positive/negative semantic cases
    execute during contract validation. Mutation checks reject missing target
    or peer ground truth. P2.57 plan/checkpoint/kernel patch are byte-identical;
    only the static userspace runtime changes, and two links are reproducible.
    The initial independent review exposed four execution-closure gaps. Exact
    generated-C execution/mutations, topology source receipts, corrected
    adapter labels, and fail-closed direct-collector envelope checks close
    them; final independent review returned `GO`. A later build-boundary audit
    corrected one stale conclusion: byte-identical base/template patches do
    not imply candidate Image reuse because the source-contract domain and
    receipts derive a new run ID, UNSAT tag, and final config patch. The first
    reproducible A/B and package pair then exposed a strict host-only
    entrypoint mismatch: the P2.58A adapter inherited P2.57's init address.
    The corrected source-bound adapter owns an isolated `0x401580` init and
    `0x4000cc` child contract, restores historical state on every path, and is
    checked against a real two-link userspace build before Full LTO. Fresh
    intent, two clean byte-identical builds, deterministic package pair,
    independent closure, offline promotion, and connected D0 passed.
42. **P2.58A complete/closed, F1:** one exact candidate and rollback transfer
    completed. Generation 80 passed exact real-UDC membership at `0x87`;
    generation 81 reached terminal `0x8f`. Two byte-identical retained reads
    contain one accepted exact record. Final health and all eight timeline
    events passed; authority is consumed.
43. **E3-E4 next:** design one bounded ACM banner over the now-proven real UDC,
    then separately prove one nonce exchange. Do not infer enumeration or ACM
    from E2, and do not expand to shell, NCM, Debian, or hot reload.
44. **P2.59 E3 focused analysis complete, H0:** the exact qualified kernel has
    configfs, libcomposite, generic ACM, and gadget serial built in; its exact
    binary proves function creation registers `ttyGS0`, disconnected writes
    queue in the TTY FIFO, and later `gserial_connect` starts transmission.
    Keep the 60-module plan. Queue one exact banner before peripheral-mode and
    UDC bind, keep the gadget-side FD open, and use the spare `0x88..0x8e`
    stages before terminal `0x8f`. Historical M34/O3F misses do not contradict
    this path because they predate the proven provider chain or lack internal
    coordinates. The remaining structural gap is a typed Process v2 ACM
    observer plus strict retained-terminal-and-host-bytes `all_of` acceptance.
45. **P2.59 independent adversarial review complete, H0:** a same-session
    Claude Opus 5 `xhigh` pass returned `GO_WITH_MUST_FIX`. Independent
    reconciliation accepted four execution gaps: the current runner cannot
    express E3 `all_of`, gadget-side termios is not raw, the host ACM observer
    lacks interference/exclusive-ownership control, and resume cannot yet
    re-derive a durable ACM receipt. Its fifth claim, unresolved SSUSB driver
    identity, is ruled out by the exact accepted
    `msm-dwc3/a600000.ssusb` gate and matching FYG8 source. Do not reopen that
    provider question.
46. **P2.60 E3 ACM-banner design complete, H0:** preserve the exact P2.58A
    prefix and append stages `0x88..0x8f`, then move terminal to `0x90`
    (generation 89). The candidate creates one high-speed generic ACM gadget,
    opens `ttyGS0` raw without flush, queues one run-ID-derived 49-byte banner,
    keeps that FD open, uses idempotent peripheral role selection, binds the
    exact UDC, and requires `state=configured/current_speed=high-speed`.
    Process v2 gains one optional typed ACM observer, a candidate-exact
    transient ModemManager udev exclusion, exact topology/TTY ownership, an
    immutable raw receipt, resume re-derivation, and strict
    retained-plus-ACM `all_of`.
    Retained-only and ACM-only results are named diagnostics. Odin, rollback,
    the 60-module plan, the state machine, and the eight timeline names remain
    unchanged.
47. **P2.61 complete, H0:** the P2.60 source contract, generic exact CDC-ACM
    observer, source-derived manifest binding, ModemManager/UID continuity,
    raw-first receipt, durable resume, E3 verdict matrix, and legacy
    retained-only regression are implemented. Real-pty and mutation fixtures
    cover prequeued/split/extra bytes, exact endpoint ownership, malformed
    evidence, crash/abort/report paths, and rollback-safe observer faults.
    Focused integration passed 112 tests. GPT-5.6-sol and Claude Opus 5
    independent reviews both returned `GO` after their findings were repaired.
    No kernel, image, device, D0, or live authority was created.
48. **P2.62 next, H0 then D0:** derive one fresh P2.60 intent, pass the cheap
    linked userspace closure, run the final clean Full-LTO A/B qualification,
    linked audits, deterministic package pair, and private E3 Process v2
    manifest/offline promotion. Then run connected D0 and stop at a fresh
    exact F1 approval token. No F1 transfer occurs without that new token.
49. **P2.62 first qualification stopped, H0:** two clean Full-LTO builds and
    deterministic AP archives were byte-identical, but independent static
    closure correctly stopped promotion. The P2.60 adapter still inherited
    P2.42's blanket configfs/`ttyGS` prohibition even though the exact P2.60
    source-bound runtime requires that bounded E3 authority. This is a stale
    versioned host-contract defect, not unexpected candidate authority.
    P2.60 now owns an exact 67-string absolute-path inventory, exact sensitive
    hex/function/speed/role/UDC sets, and a pinned E3 runtime-source SHA; it
    keeps block, shell, and `sec_log_buf.ko` authority forbidden, scopes its
    override with `finally`, and leaves P2.42/P2.58A unchanged. Removal,
    sibling-capability, short-path, uppercase-hex, exception, and nested-call
    mutations pass, and final independent review returned `GO`. The first
    intent and builds are not promotable because the corrected adapter is
    source-receipted. Derive a new intent and repeat A/B.
50. **P2.62 v2 Build A complete; Build B preflight stopped, H0:** the fresh
    intent, two-link userspace/entrypoint/authority closure, Build A preflight,
    and clean Full-LTO Build A passed. Its immutable bundle was locally
    rehashed. Build B preflight then rejected twice because the operator
    removed repository-root `out/` instead of the wrapper-owned
    `$SOURCE_TREE/out`; the second durable stderr proved the same exact clean
    gate. No Build B or device action started. Fails-twice stops that unit.
    The runbook now requires canonical-parent verification and names only
    `$SOURCE_TREE/out`. Resume, if any, is a new H0 recovery unit from the
    unchanged intent and frozen Build A, never a reuse of either failed
    preflight directory.
51. **P2.63 artifact-safety closure, H0:** the recovered v2 Build B completed,
    all six linked artifacts matched Build A byte-for-byte, and the P2.60
    linked audit passed. Promotion then stopped before candidate packaging:
    the generic E2 package metadata falsely claimed no userspace sysfs or
    configfs writes, while exact P2.60 intentionally performs bounded SSUSB
    role and CDC-ACM configfs writes. The builder now selects safety by exact
    source contract, the static checker consumes that single definition,
    historical E2 semantics remain unchanged, and P2.60 source-receipts both
    E3 scope strings. Complete independent map fixtures, every-field mutation,
    and an AST call-site mutation close the first independent-review finding;
    final re-review is `GO`. Compilation, 31 focused tests, and diff checks
    pass. Because the builder is source-bound, v2 remains diagnostic only.
    Derive v3 and repeat A/B before package, D0, and F1 preparation.
52. **P2.63 v3 E3 candidate approval-ready, H0+D0:** one fresh corrected intent
    passed the exact two-link userspace closure. Clean Full-LTO builds A and B
    completed in `38:25.60` and `39:03.99`; all six reproducibility artifacts
    were byte-identical, neither build swapped, and the P2.60 linked audit
    passed. Two deterministic boot-only packages, independent artifact
    closure, offline Process v2 promotion, ready-manifest validation, and live
    plan rendering passed. The first connected D0 stopped read-only because a
    historical E2 marker remained in the baseline; no Odin or transfer began.
    One authorized normal Android reboot rotated it out. A new D0 then proved
    one healthy FYG8 target, clean baseline, exact rollback, and unchanged
    execution closure and emitted one fresh private approval binding. No F1 is
    authorized or executed. Next is only the exact P2.60 E3 approval token,
    followed by one boot-only candidate attempt and mandatory rollback.
53. **P2.64 qualification-latency postmortem, H0:** detailed source and history
    reconstruction plus one persistent-session Claude Opus 5 maximum-effort
    adversarial review confirm that four of six Full-LTO builds were avoidable.
    The line failed closed safely; no device-safety defect was found. The two
    rejected pairs were decidable from the frozen intent or already-linked
    `/init` before Build A, but host verifier, package-metadata, and evidence
    receipts currently feed the run-ID preimage and turn their correction into
    a kernel-config change. The post-F1 remediation is deliberately staged:
    first correct the runbook lane table, then add one pre-LTO rehearsal, then
    split payload identity from qualification/provenance and package/live
    identity with exhaustive mutation tests and independent review. Do not
    implement that split before the prepared E3 transaction closes: the exact
    candidate, D0 result, approval binding, and execution closure remain
    unchanged. See the P2.64 qualification-latency postmortem.
54. **P2.65 E3 pre-candidate host-guard abort, F1 then H0:** one exact P2.60
    approval matched and the execution D0 recheck passed, but the runner
    aborted at `APPROVED` before Download because the ordinary-user `mmcli`
    inhibition call was rejected by the installed root-only ModemManager
    D-Bus policy. The durable journal proves candidate `not-attempted`, no
    Download/Odin/transfer, no rollback required, and the device remained
    healthy FYG8 Android with root. The observer now uses attended
    `pkexec -> root setpriv(PDEATHSIG) -> mmcli`, preserving device-scoped
    inhibition and adding bounded private failure evidence. Python
    compilation, 24 observer tests, 61 Process v2 core/live integration tests,
    and one harmless attended root-broker/control-pipe host probe pass. The
    aborted transaction and approval token are not reusable. This fixed the
    authorization defect but not the deeper API mismatch; item 55 supersedes
    its device-scoped inhibition strategy.
55. **P2.66 E3 second pre-candidate host-guard abort, F1 then H0:** a fresh
    exact approval and execution D0 recheck passed, but root `mmcli` returned
    `WrongState: Modem not exported in the bus`. The runner again stopped at
    `APPROVED`: candidate `not-attempted`, no Download/Odin/transfer, no
    rollback, and healthy Android retained. Upstream source proves
    `InhibitDevice` only accepts an already probed and exported modem, so it
    cannot protect a future ACM interface. Replace that invalid assumption
    with one `/run/udev/rules.d` candidate-exact transient rule, always armed
    before Download and removed on release, parent death, or bounded
    self-timeout. The root process executes only an argv-frozen, stdlib-only
    `python3 -I -B -c` helper, validates the exact rule grammar/hash, and uses
    absolute privileged binaries. The endpoint must expose both ModemManager
    ignore properties before open. No global service stop or persistent host
    policy change is allowed. The first independent review returned `NO-GO`
    on inactive-state false-arm, nonzero cleanup, writable-script TOCTOU, and
    privileged path resolution; all four are repaired. Release cleanup is now
    current-instance-bound and part of normal/resumed proof, stale or nonzero
    cleanup forces no-proof after rollback, and an isolated uid-0 lifecycle
    test proves verify/reload/release/unlink/reload ordering. Final independent
    review is `GO` and 109 focused Process v2 tests pass. Commit `f270e859`,
    offline adapter-v3 closure, and a fresh connected D0 all pass against the
    unchanged candidate bundle. The new private run has no transaction, Odin,
    transfer, reboot, or device write and holds one fresh exact approval
    binding. No F1 is authorized until that token is submitted.
56. **P2.67 E3 configfs-stage failure, F1 then H0:** one exact P2.60 v3
    candidate and one exact Magisk rollback transferred once. The operator
    observed a successful candidate boot and no boot loop, but no ACM endpoint
    appeared. Two byte-identical retained reads preserve the proven real-UDC
    stage `0x87`, item 11, then terminal failure at the first E3-local stage
    `0x88`, item 0, with detail 5. Source mapping identifies
    `p260_mount_configfs()`. Its expected magic is incorrectly the sysfs value
    `0x62656572`; Linux configfs uses `0x62656570`, so the candidate cannot
    pass a correct configfs `statfs` result. The retained detail cannot
    separately identify a syscall-returned `EIO`. The initial final-health
    pass stopped after rollback on measured USB inventory; durable recovery
    repeated no transfer and closed final Android/root/partition health. The
    verdict is `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, authority is consumed,
    and the next unit is only the narrow H0 constant correction plus a
    semantic source-contract test before any fresh build, D0, or approval.
57. **P2.68 configfs semantic-gate correction complete, H0:** change only
    `P260_CONFIGFS_MAGIC` from sysfs `0x62656572` to configfs `0x62656570`,
    update its source receipt, and add an external-constant parser for all 16
    E3 runtime ABI literals to the selected pre-LTO source contract. The gate
    compares against one contract table before generic SHA identity, requires
    one exact definition per macro, and rejects wrong-value, missing, and
    duplicate mutations through the real `_generated_semantics()` path. The
    build runbook now records that byte identity and token presence do not
    validate external semantics and requires load-bearing literals to be
    registered and mutation-tested.
    Python compilation, the focused mutation, all 14 P2.60 contract tests,
    and the actual no-LTO userspace two-link closure pass. No Full-LTO build,
    intent, image, package, D0, approval, or device action occurred. Next is a
    fresh source-bound intent and final qualification, not more USB analysis.
58. **P2.69 corrected E3 candidate host-ready, H0:** derive one fresh P2.60
    intent and run two clean same-path Full-LTO builds. Builds A/B finish in
    `40:43.23`/`40:45.31`, peak near 24.25 GiB, use no swap, and match across
    `.config`, `Image`, `System.map`, `abi.xml`, `vmlinux`, and
    `vmlinux.symvers`. Linked semantics, deterministic boot-only package
    equality, independent closure, and offline promotion pass. A final host
    audit catches promotion/acceptance using legacy terminal `0x8f` rather
    than selected P2.60 terminal `0x90`. This is downstream-only: preserve the
    immutable candidate and A/B bundles, quarantine only the stale Process v2
    and ready-manifest outputs, fix one version-aware terminal selector, and
    regenerate those outputs. Focused 28+17 tests pass, the new bundle
    validates with `0x90`, and a stale `0x8f` mutation is rejected. No D0,
    approval, Odin, transfer, reboot, or device write occurred. The next
    attended step was connected D0 and one fresh exact F1 approval. This
    candidate was instead retired before D0 by P2.70's exact QEMU result.
59. **P2.70 generic E3 execution and configfs-link correction, H0:** execute
    the exact P2.60 configfs/ACM helpers in a generic-arm64 QEMU guest before
    spending another F1. The P2.69 runtime fails gadget creation because
    configfs resolves `../../functions/acm.usb0` from PID1's `/` working
    directory. An absolute creation target reaches configfs, whose canonical
    readback is `../../../../usb_gadget/g1/functions/acm.usb0`; the old
    candidate rejects that value too. Split creation/readback strings, bind
    both into the authoritative source contract, and retain only an exact
    promotable QEMU verdict. The corrected runtime passes configfs mount,
    gadget construction, `ttyGS0`, pre-bind banner queuing, dummy-UDC bind,
    configured state, and exact 49-byte `ttyACM0` receipt. Focused tests,
    historical host regressions, fresh intent, and two-link userspace closure
    pass. P2.69's frozen outputs remain untouched and live-ineligible. No
    Full-LTO, D0, approval, Odin, transfer, reboot, or device write occurred.
    Next is clean Full-LTO A/B on the qualified build host, then linked audit,
    deterministic package/static closure, and offline promotion.
60. **P2.71 ELF-authority correction and E3 candidate host-ready, H0:** the
    first P2.70 pair reaches independent closure, which falsely requires the
    incidental ELF string `"/8@"`. A diagnostic correction proves no later
    blocker. Split required paths from optional ELF artifacts while retaining
    fail-closed rejection of missing required and unregistered paths. Focused
    mutation tests and the exact new linked userspace pass before Full LTO.
    Fresh Builds A/B finish in `39:30.23`/`38:20.13`, use no swap, peak at
    `69.5 C`, and match for all six linked artifacts. GNU linked audit,
    deterministic boot-only packages, independent closure, and offline
    Process v2 promotion pass. An earlier LLVM substitution is recorded as a
    runbook violation; immutable bundles were instead audited with GNU tools
    in about 21 seconds. No ready manifest, D0, approval, Odin, transfer,
    reboot, or device write occurred.
61. **P2.72 E3 data-only ready manifest, H0:** bind the exact P2.71-promoted
    AP, rollback, offline contracts, terminal `0x90`, source closure, and
    CDC-ACM observer into one reusable Process v2 manifest. Common-runner
    preflight and exact-bundle regression pass; a stale runner draft is
    rejected. No device contact or authority occurred.
62. **P2.73 freeze and attended rehearsal, H0:** freeze the complete P2.72
    execution closure, pin its command/path/hash sequence, and preserve the
    journal-only recovery branch. Localize the repeated rollback deviation to
    a pre-snapshot USBFS race; exact inner exception remains unresolved. No
    device contact or authority occurred.
63. **P2.74 host USB trace sidecar, H0:** add one bounded non-authoritative
    kernel/udev/`lsusb` sidecar across candidate, rollback, recovery, and final
    health. It never opens candidate ACM; raw identifiers remain private.
    Python compilation and five focused tests pass.
64. **P2.75 P2.72 F1 adversarial preflight, H0:** inspect the frozen execution,
    recovery, artifacts, sidecar, stock evidence, and journal states. Focused
    tests plus exact bundle/closure validation pass; no authority occurred.
65. **P2.76 E3 observation-margin correction, H0:** the P2.58A retained record
    cannot prove margin in 120 seconds. Retire ready1 and select unchanged
    ready2 with a 180-second bound; offline validation passes.
66. **P2.76 E3 post-bind timeout, F1:** ready2 reaches configfs, gadget,
    `ttyGS0`, queued banner, peripheral readback, exact UDC membership, and
    exact UDC bind at `0x8e`; `0x8f` times out before configured/high-speed and
    no ACM endpoint is accepted. Exact rollback and final health pass; the
    transaction closes and authority is consumed.
67. **P2.77 post-bind source analysis, H0:** separate stale retained text,
    rule out external firmware requests in the exact 60-module closure, and
    trace the asynchronous `mode_store -> sm_work -> start_peripheral` path.
    Stage `0x8e` proves the synchronous initial pull-up returned success, not
    later host attach or enumeration.
68. **P2.78 three-lane USB analysis, H0:** stock needs no hidden minimal-ACM
    enable write, while P2.76 does not prove that its parent role transition
    executed or settled. Preserve exact role/UDC state and armed host tracing.
69. **P2.79 role-settle closure, H0:** UCSI can structurally reach the parent
    callback, but no stable parent-work completion attribute exists. Its
    activation in the exact candidate remained untested.
70. **P2.79A PMIC GLINK/UCSI activation closure, H0:** both modules are in the
    exact 60-module plan, but their ADSP RPMSG owner `qcom_q6v5_pas.ko`, GLINK
    subdevice registration, and firmware path are absent. Extcon/default and
    Samsung-notifier producers are also inactive, so P2.76's PID1 peripheral
    write is source-deduced but not separately live-proved. Retire UCSI-race
    and role-retrigger as the P2.80 headline; design a minimal parent-worker
    progress discriminator next. No device contact or authority occurred.
71. **P2.80 parent/pull-up discriminator, H0+D0:** source, QEMU 5/5, Full-LTO
    A/B equality, linked/package/static/promotion, ready1, and D0 gates pass.
72. **P2.80 closed plus correction, F1+H0:** retained `0x8e/detail=0` then
    `0x8f/detail=0xb22` proves RUN_STOP plus `DEVCTRLHLT` clear while UDC stays
    `not attached`; exact rollback/final health pass. External eUSB2 repeater
    is ruled out, while discarded `current_speed` and host exit cause remain.
73. **P2.80 resume/femto/EUD audit, H0:** exact source and modules reject a
    parent-PM sign or one `hs_phy->flags` sample as electrical proof. Reuse the
    trace lifecycle only through a versioned ordered discriminator; do not
    infer electrical readiness from swallowed clock errors.
74. **P2.80 child-reinit closure, H0:** child DEVICE suspend/resume fully
    reinitializes PHY; use one fenced parent role cycle, never as rail proof.
75. **P2.82 decision contract, H0:** freeze mechanism search, keep the 45-byte
    geometry, and execute classifier `46/46` plus 567 tuples. No live authority.
76. **P2.82 implementation and pre-LTO qualification, H0:** generated
    classifier `46/46`, tuples `567/567`, lifecycle `5/5`, and all `19/19`
    gates pass, including portable temp-repo producer-to-consumer preflight.
    Full-LTO/AP/F1 remain undone.
77. **P2.83 stock USB reset trace, D0+D1:** stock EUD enable is `0`, both
    vendor-module hashes match P2.82, and all probe targets exist. One bounded
    `resetUsbGadget` returned zero but produced no ADB, host-USB, or trace
    transition; cleanup and Android/root health passed. Treat it as a no-op,
    not a positive control. A physical reconnect requires a fresh D1 approval.
78. **P2.83 stock physical-reconnect trace, D1:** one fresh approval captured
    50 balanced events and real SuperSpeed return. The successful suffix is
    parent resume, child resume, femto-HS init, RUN_STOP on, then
    notify-connect; cleanup and Android/root health pass. This supports the
    P2.82 child-reinit mechanism but does not alter or authorize its F1.
79. **P2.83 stock high-speed control, D1:** after one guarded active-bind
    refusal and clean removal, a fresh approved UDC unbind/HS/rebind plus
    physical reconnect captured the same 14-event success suffix at high
    speed. Original super-speed-plus configuration, active SuperSpeed,
    tracefs, and Android/root health were all restored.
80. **P2.82 candidate closure and connected preparation, H0+D0+D1:** Full-LTO A/B,
    GNU linked audit, deterministic AP A/B, independent static closure,
    offline promotion, exact ready manifest, and common-runner host preflight
    pass. Two host adapters now preserve the inherited P2.80 entrypoint and
    60-to-59 module view for P2.82 without changing candidate identity. The
    connected D0 found one stale same-family retained record but no exact
    P2.82 run ID, so it stopped before preparation or authority. One fresh
    exact D1 Android reboot rotated that history with return health intact;
    repeated D0 passed and emitted a private fresh F1 approval binding. No
    Download, Odin, transfer, candidate boot, or F1 authority occurred.
81. **P2.82 controlled-reinit F1:** one exact candidate and rollback transfer
    completed with no candidate replay. Two byte-identical retained reads show
    `0x8d/detail=0`, then terminal `0x8e/detail=0xc10`
    (`none-readback-not-reached`). The exact NONE-write helper completed, but
    the reader stripped sysfs newline before comparing with newline-bearing
    readback constants, so `0xc10` is a comparator false negative and says
    nothing about whether NONE was reached. Later child-reinit and E3 boundaries
    remain unexecuted. Exact rollback and final health passed; authority is
    consumed.
82. **P2.84 sysfs ingestion correction and prepared candidate, H0+D0+D1:**
    preserve P2.82 kernel inputs,
    classifier, retained ABI, module plan, and linked tables byte-identically;
    derive newline-bearing write wire and normalized readback from one token.
    Exact FYG8 `mode_show` and `runtime_status_show` sources plus the unchanged
    reader are pinned and executed in an AArch64 oracle. Userspace two-build,
    current generic QEMU receipts, linked audit, and all `20/20` pre-LTO gates
    pass. Independent review also separated the qualification-only oracle from
    candidate identity, bound the P2.84 source-check ID, and added relocation,
    tamper, runtime-mutation, and historical-receipt rejection tests. P2.82
    remains registered for historical evidence parsing but is mechanically
    rejected by new-candidate selection, intent parsing, and contract
    verification as superseded by P2.84. Fresh run
    `023060c8dd0ab036f8547a816624356f` passes the production `20/20` gate.
    Clean Full-LTO A/B match across all six artifacts; boot-only AP A/B,
    independent static closure, offline promotion, exact ready manifest, and
    common-runner host preflight pass. The first D0 found the exact consumed
    P2.82 `0x8e/detail=0xc10` record and zero exact P2.84 records, then stopped
    before preparation. One freshly approved exact normal reboot returned the
    same healthy FYG8 Android/root target and rotated that history. Repeated D0
    passes with a clean `0/0` baseline and a private immutable approval binding.
    No Download, Odin, payload transfer, F1 authority, or live authority occurred
    in this preparation unit; its binding was later consumed by unit 83.
83. **P2.84 controlled-suspend boundary, F1:** one exact candidate and rollback
    transfer completed with no candidate replay. The operator reported a normal
    candidate boot with no boot loop, while the 300-second observer accepted no
    ACM endpoint. Two byte-identical retained reads show progress
    `0x8e/detail=0`, then `0x8f/detail=0xc18`: corrected NONE readback, the
    traced stop-peripheral function return, exact child `suspended` status, and
    zero-return power-off helper are proven. Outer-work return, helper
    electrical effect, DEVICE restart/readback, child resume, PHY reinit, bind,
    final bus state, and ACM remain unproved because no `0x90` or later
    checkpoint survived. Exact rollback/final health passed; the transaction is
    closed and approval consumed. Do not replay P2.84.
84. **P2.84 post-`0x8f` restart-gap localization, H0:** exact descriptors prove
    the so-called worker probe is only `dwc3_otg_start_peripheral`, leaving the
    enclosing stop-side `dwc3_otg_sm_work` unmeasured. The immediate DEVICE
    write synchronously flushes that prior work; its helper's 30-second expiry
    then sends `SIGKILL` followed by unbounded blocking `wait4`. Both retained
    slots remain valid, proving no `0x90` write reached its first durable
    CRC-clear. This path explains the silence but not why the parent stop
    worker failed to return. A fence is diagnostic if that worker is wedged.
85. **P2.84 gap-review correction and stock discriminator, H0+D0:** exact source
    proves HS-PHY power-off is nested inside child runtime suspend, before
    stop-peripheral return and the later outer parent suspend; a PID1 fence
    cannot reorder it. `perf_vote_work` uses `system_wq`, not ordered
    `k_sm_usb`; its prior cancel returned and no re-enable follows. The refined
    stock D1 ranks exact parent offsets, uses ungated
    `NONE -> suspended -> PERIPHERAL`, suppresses a too-short control window,
    and records every `mode_store` comm/PID. The permanent attachment-name gate
    passes the new contract. D0 found no network address, so TCP ADB is
    excluded. Positive is decisive; negative is not bare-PID1 clearance. No D1
    or F1 authority exists.

Do not reactivate R4W1-C3, create a per-candidate host/live execution helper,
reuse a consumed approval, load `sec_log_buf.ko` in a checkpoint-bearing
native candidate, or infer bind from module registration. The bounded
in-runtime P2.80 write child is not a separate execution helper.

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
