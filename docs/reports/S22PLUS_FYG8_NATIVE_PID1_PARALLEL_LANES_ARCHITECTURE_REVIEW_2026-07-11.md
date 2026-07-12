# S22+ FYG8 Native-PID1 Parallel-Lanes Architecture Review

Date: 2026-07-11 KST
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`
Scope: host-only, read-only architecture review; no build, image generation,
device contact, flash, or commit
Review session: Claude Opus 4.8 session
`c43595a1-fd84-4563-bf9a-e3831cc44331`

## Purpose

This record captures the two-round Claude architecture discussion performed
after a repository-wide evidence review. It is a decision record, not a live
authorization and not proof of any untested S22+ behavior.

The final target remains:

```text
S-Boot/ABL
  -> FYG8-compatible kernel
  -> project-owned /init as global PID1
  -> early witness
  -> watchdog/module/hardware bring-up
  -> Android-independent host control
  -> persistent rootfs / pivot_root
  -> Debian or other native services
```

Android and Magisk are retained only as a known-good bootstrap, recovery, and
measurement baseline. They are not the final product architecture.

## Evidence Baseline

The discussion initially treated the following as verified within their stated
scopes. The subsequent exact-build bootloader/reboot-reason audit corrects the
M4T3 and S10C0 interpretation without changing their raw run artifacts. See
`docs/reports/S22PLUS_FYG8_BOOTLOADER_REBOOT_REASON_AND_RETAINED_MEMORY_STATIC_RE_2026-07-11.md`.

- M4T2: a custom raw `/init` produced the attended stable park behavior and
  remains the strongest positive native-PID1 floor.
- M4T3: a later Odin endpoint was observed after a first-action
  `reboot(..., "download")` candidate, but M21 already downgraded this to
  timing-ambiguous. Exact static RE now shows that the required modular Samsung
  command parser/reason writer was absent, so it is not first-syscall proof.
- M31B: the watchdog dependency closure permitted 120 seconds of survival. It
  did not prove direct-PID1 USB, storage, Debian, or a retained marker.
- O1.1: framed `ttyGS0` control works under the stock-first-stage,
  Android-derived environment. It does not prove direct-PID1 USB.
- O3/O3F: the tested direct-PID1 ACM implementations did not enumerate. This
  is a controlled negative for those implementations, not proof that `/init`
  did not execute.
- V3428R: the stock retained-ring transition works as a positive control.
- V3433: the direct-PID1 marker result is `NO_PROOF`.
- V3439: ramoops registered and bound, but retained zero current-run records
  across the tested SysRq/RDX/reset path.
- V3440: Samsung RDX USB and the preamble exchange were reached, but the exact
  NegativeAck stopped before probe or transfer.
- R0: source, toolchain, IKCONFIG, and the initial 441-module first-stage
  baseline passed host audit. Full-LTO R1 has not completed.
- The known Magisk v30.7 boot kernel is the stock kernel plus the audited
  3-byte DEFEX and 6-byte PROCA changes. RKP and legacy-SAR patterns were
  no-ops, and the embedded Samsung security configs remain enabled.
- P0 snapshots recorded 441 vendor-ramdisk modules, 356 `/vendor_dlkm` files,
  and 482 loaded `/proc/modules` entries. These counts describe different
  sets and do not establish one closed compatibility corpus.

## Overall Decision

The target architecture remains plausible, but the previous serial order was
mis-prioritized. Kernel rebuild trust work and early-PID1 observation work must
proceed as parallel lanes and converge only when a rebuilt-kernel live gate is
ready.

### Lane W - Native-PID1 witness and discrimination

Goal: establish a valid host-visible transition, then raise the deepest
positively proved native-PID1 checkpoint.

- Exact FYG8 ABL maps stored PON reason `0x15` to Download/Odin.
- Exact FYG8 LinuxLoader also converges mission-boot load/authentication failure
  and a returned `BootLinux()` handoff onto Odin. Odin is a non-unique sink.
- The Linux `"download"` parser and PON writer are modules. They were absent
  from M4T3, M21A, and M34 S10C0; `qcom-scm` alone performs reset without
  encoding `0x15`.
- First design a producer positive control that loads and binds the exact
  reboot-reason dependency closure, plus an otherwise matched generic-reset or
  park control.
- That design is now specified in
  `S22PLUS_FYG8_LANE_W_REBOOT_REASON_PRODUCER_CONTROL_DESIGN_2026-07-11.md`.
  Static source review found that the earlier seven-module hard closure omitted
  the modular SPMI/SDAM nvmem provider path. The selected future differential is
  W0 full-closure park, W1 matched Recovery sink, then W2 Download positive.
  Exact LinuxLoader maps `0x01` to mode 2 and its explicit Recovery branch.
  W1 must additionally prove the live `/soc/reboot_reason` binding under
  `qcom-reboot-reason`; Samsung's pre-defined Recovery handler intentionally
  leaves the PON write to that Qualcomm notifier.
  The Samsung parser's platform bind is also not readiness proof because its
  command hooks register asynchronously after probe. The candidate must parse
  the exact mutex-protected debugfs command list and prove both terminal
  handlers are present before reboot.
  It must also gate exact `qcom_scm` and `qcom-dload-mode` bindings because the
  Samsung reason writer arms dump mode during probe and the bound dload
  notifier is what clears it on a clean reboot.
  These checks are phased load barriers: a final all-modules poll cannot repair
  a one-shot asynchronous command-registration failure.
  The three controls must reuse one byte-identical init; only an equal-length
  five-byte ramdisk mode token may differ after normalized unpacking.
- Do not use Download as a checkpoint beacon until that control proves the
  producer path and excludes generic reset, `PARAM_BOOT_DOWNLOAD_FAIL`, and
  mission-boot load/authentication fallback.
- Design this control and later checkpoint candidates before R1; this needs no
  kernel build.
- Treat Download absence as inconclusive. It must never be translated to
  "PID1 did not run" or "checkpoint was not reached."
- Recovery, poweroff, and normal reboot are not accepted beacons until each
  has an independent host-classification positive control. Normal reboot is
  confounded with watchdog and crash reset and is unsuitable by default.
- This report authorizes design only. Any candidate build, boot flash,
  repeated confirmation, or live bisection needs a new narrow SHA-pinned
  `AGENTS.md` exception and explicit operator approval.

### Lane K - Kernel build trust, ABI compatibility, and instrumentation

Goal: produce an admissible rebuilt-kernel artifact, prove its static vendor
compatibility, and use it as an instrumentation or configuration lever only
when justified by evidence.

- R1 proves provenance-bound buildability only.
- R2 proves static kernel/module/KMI compatibility only.
- A rebuilt kernel may permit a better early witness, but this is a hypothesis.
  V3439 may reflect S-Boot/reset-path clearing, dynamic ramoops placement, or
  record-header invalidation. Kernel changes cannot be assumed to repair it.
- Samsung security configuration changes remain deferred until a named,
  measured dependency blocks a specific next step.

## Corrected R1 Contract

R1 artifact ownership is divided into three classes.

### Required build outputs

R1 must require the outputs that the pinned kernel build actually owns:

- `Image` or the exact configured compressed Image form;
- `vmlinux`;
- `System.map`;
- generated `.config`;
- `Module.symvers` or the build tree's exact symvers output;
- generated `.ko` modules and compiled DTBs only when the pinned Samsung/GKI
  build rules actually emit them.

Presence, nonzero size, expected file type, and hashes are mandatory. A zero
return code with a missing required artifact is FAIL.

### Pinned inputs

Stock DTBO, `vendor_boot`, `init_boot`, and vendor ramdisk artifacts are inputs
unless the R1 build rules explicitly generate them. Their hashes must be
pinned, but R1 must not claim to have built them.

### Later derived packages

Repacked boot images and Odin AP containers belong to later packaging/live
units. Their absence cannot fail R1.

R1 also requires:

- source-tree and overlay hashes bound into preflight;
- exact toolchain identity verified against the R0 audit;
- a minimal allowlisted environment rather than ambient host `PATH` state;
- generated IKCONFIG comparison against the stock evidence;
- pinned build metadata or a documented nondeterminism set;
- durable Full-LTO resource and failure logs;
- a complete versioned host-tool manifest;
- correction of stale root-document pins in the transfer manifest.

R1 PASS means only: a provenance-bound, allowlisted build produced all
artifacts owned by R1. It does not prove boot viability or stock equivalence.

## Corrected Module and R2 Contract

The module problem is split into three independent claims.

1. **On-disk corpus closure:** enumerate the shipped union from vendor ramdisk,
   `vendor_dlkm`, `system_dlkm`, any other mounted module source, and
   `modules.builtin`.
2. **Static consumed-symbol compatibility:** every `__versions` CRC consumed by
   the intended shipped module union must be satisfied by the rebuilt
   kernel's `Module.symvers`; module release and `vermagic` rules must also
   match.
3. **Runtime loaded-set parity:** compare against a pinned stock/Magisk baseline
   captured at the same boot milestone and under the same workload. The P0
   count of 482 is not an invariant for every boot.

Module identity must not rely on filename or module name alone. The audit
should use normalized module name, `srcversion`, `vermagic`, and decompressed
content hash, while resolving built-ins through `modules.builtin`. Aliases,
duplicate names, and compressed `.ko` forms must be handled explicitly.

Minimal static R2 PASS requires:

- kernel release and `vermagic` compatibility;
- closed on-disk corpus provenance;
- consumed-symbol CRC compatibility for the declared corpus;
- zero unexplained KMI breakage against the pinned GKI ABI policy;
- an empty or fully explained generated-config delta;
- an explicit stock-DTB/DTBO boundary and binding compatibility check;
- every residual Image difference explained without requiring byte identity.

Runtime loaded-set parity is a later live check and must not be presented as a
completed static R2 result.

## 2026-07-11 Host-Gate Implementation Result

The corrected contracts above are now implemented rather than merely planned.

- R1 preflight reruns exact source-overlay verification, uses an allowlisted
  environment, and fails a zero-return build with missing owned artifacts or
  zero generated modules.
- Exact FYG8 super metadata and recursive F2FS inspection close the on-disk
  corpus at 491 unique module names. `system`, `vendor`, and `odm` contain no
  `.ko`; `vendor_dlkm` contributes 50 names not in vendor ramdisk.
- The complete consumer CRC contract is 25,864 rows over 4,619 symbols.
- The R2 auditor consumes all returned symvers files, but remains fail-closed
  until a schema-v2 Full-LTO R1 result exists. No rebuilt-kernel or live claim
  follows from this host work.

Implementation report:
`docs/reports/S22PLUS_FYG8_KERNEL_REBUILD_R1_R2_HOST_GATES_2026-07-11.md`.

## First Rebuilt-Kernel Live Gates

The previous roadmap made the Magisk-equivalent candidate the first live
rebuild proof. The corrected order separates kernel viability from rooted
measurement.

### Gate A - unpatched rebuilt kernel, stock userspace carrier

Preferred first live proof:

- use the unpatched R2-GO kernel;
- preserve the selected stock ramdisk/userspace carrier;
- require no root-dependent postchecks;
- prove only that the rebuilt kernel reaches a bounded host-visible normal
  Android state on this hardware and that the exact boot-only rollback works.

Gate A does not prove complete module ABI closure, native PID1, or root. DEFEX
impact on root remains empirical; do not state that it blocks all root.

### Gate B - Magisk-equivalent measurement carrier

Optional later proof when rooted measurement is required:

- locate DEFEX and PROCA patch targets by audited content, never stale offsets;
- require exactly one semantically audited target for each patch;
- zero or multiple candidates are FAIL;
- compare against the rebuilt-unpatched kernel and require the intended two
  patch ranges and no additional byte changes;
- preserve and re-audit the pinned Magisk ramdisk semantics.

Gate B provides richer measurements but entangles rebuilt-kernel viability,
binary patch matching, and Magisk userspace. It must not replace Gate A or be
described as an unchanged-kernel proof.

Both gates require a future boot-only `AGENTS.md` exception, fresh artifact
hashes, explicit approval, and the existing S22+ rollback evidence. A90
`version:` or `selftest fail=0` rules are not S22+ rollback gates; S22+ must use
its Android/Magisk identity and pinned boot/DTBO/recovery hashes.

## Conditional Download One-Bit Beacon

This section is a future design contract, not an already proved primitive.
It becomes active only after the reboot-reason producer/control gate passes.

For a candidate checkpoint `N`, the raw `/init` path performs
`reboot(..., "download")` as the first unconditional action after reaching
`N`. No later path in that candidate may request Download mode.

Interpretation:

- Download present: `VERIFIED_REACHED_N`; the proved execution floor advances.
- Download absent: `NO_PROOF_AT_N`; the previous proved floor remains valid.

This is not ordinary binary search because a negative result is not reliable.
It is monotonic positive-floor raising:

1. start from the M4T2 attended raw-park floor;
2. prove the Samsung reboot-reason producer closure against a matched control;
3. place one beacon at a later linear checkpoint;
4. advance the floor only after a positive Download observation;
5. on a non-positive result, narrow checkpoints around the last positive floor
   without claiming the later checkpoint failed to execute;
6. require any future repeated confirmation through separately authorized,
  bounded live policy.
- Exact `XblRamdump.elf` proves the observed NegativeAck is selected by the RDX
  lock flag that also renders `(without Token)`. MID and HIGH both reached this
  branch; protocol mutation and further RDX commands remain retired.
- Exact `QcomWDogDxe` disables its UEFI watchdog at ExitBootServices. The
  bare-PID1 timeout is therefore post-handoff watchdog ownership, consistent
  with M31B survival after loading the stock watchdog closure.

The initial candidate checkpoints should cover the transition from trivial
PID1 execution through early mounts, module staging, watchdog closure, and the
first attempted USB/configfs operation. The exact list remains a host-only
design task.

## Evidence Labels

Use these labels consistently:

- `byte-identical-stock-kernel`: shipped stock kernel hash only;
- `static-stock-equivalent-kernel`: R1 output that passes the corrected R2
  static contract;
- `unpatched-rebuilt-kernel-live-viable`: Gate A only;
- `magisk-equivalent-kernel`: R2-GO rebuild plus separately audited DEFEX and
  PROCA changes;
- `native-pid1-download-producer-proved`: exact parser/writer closure and
  matched control establish that Download identifies PON reason `0x15`;
- `native-pid1-checkpoint-N-proved`: positive Download beacon at checkpoint N,
  valid only after the producer label;
- `NO_PROOF_AT_N`: no positive beacon, with no negative execution claim.

The A90 implementation is a method precedent on different hardware. It is not
evidence that the same kernel, witness, USB, or module path works on `g0q`.

## Documentation Corrections

The active project documents must not claim:

- stock-global-PID1 supervision is the final or primary architecture;
- the 441 vendor-ramdisk modules are the full compatibility corpus;
- R0 or Magisk semantic audit is direct progress proof for native PID1;
- ramoops or RDX remains a viable current-run witness on the tested path;
- community KernelSU or `r0q` mainline reports prove a `g0q` security-config
  recipe;
- an unpatched rebuilt kernel must provide Magisk root;
- a rebuilt kernel will necessarily repair persistent logging;
- M4T3 or S10C0 already proves a native-PID1 Download command path.

## Remaining Unknowns

- The deepest positive native-PID1 checkpoint after the M4T2 park is unknown.
- Native-PID1 binding of the Samsung reboot-command/reason-writer closure is
  unproved.
- The full shipped module union and its CRC satisfiability are not closed.
- Full-LTO R1 feasibility on the 32 GiB host remains unmeasured.
- A rebuilt kernel has not booted `g0q`.
- Kernel-side retained-witness repair is unproved and may be impossible across
  the selected reset path.
- DEFEX-active root behavior on the rebuilt kernel is unknown.
- Non-Download reboot targets are not validated as unique host beacons.
- Final cold-boot count and soak duration are policy thresholds, not verified
  facts.

## Prioritized Host-Only Work

1. Specify the exact reboot-reason module-closure positive control, matched
   generic-reset/park control, and later bounded checkpoint matrix without
   building or flashing it.
2. Harden the R1 wrapper contract around owned outputs, source/tool provenance,
   environment allowlisting, and durable evidence.
3. Reconcile the complete on-disk module corpus and encode the R2 static ABI
   predicate before spending the 32 GiB build-host run.

Lane W design and Lane K host hardening can proceed in parallel. Neither this
record nor the Claude discussion grants device or flash authorization.

## Claude Usage Record

The first review and the adversarial correction both used Claude Opus 4.8 with
high effort and no Claude tools. The correction turn reported 7,468 output
tokens, approximately USD 0.99, and about 119 seconds. The account UI moved
from approximately 13 percent to 28 percent current-session usage and from 38
percent to 40 percent weekly usage during the complete discussion. No code or
repository file was changed by Claude.
