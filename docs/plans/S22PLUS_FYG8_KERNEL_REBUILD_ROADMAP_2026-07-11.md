# S22+ FYG8 Kernel Rebuild Roadmap

Date: 2026-07-11 KST
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`
Scope: host-only planning and build validation; no device contact or flash

## Decision

An FYG8-derived kernel rebuild is a viable research branch, but it is not yet a
proven boot path and is not a guaranteed retained-witness solution. Native-PID1
observation and kernel build trust now proceed as parallel lanes:

1. **Lane W - witness/discrimination:** first prove the native-PID1 producer
   path for Samsung PON reason `0x15`, then design a one-bit checkpoint sequence.
   Exact FYG8 ABL maps stored `0x15` to Odin, but M4T3, M21A, and S10C0 lacked
   the modular Samsung command parser/reason writer. M4T3 is not a proved
   beacon. M4T2's attended raw park remains the strongest positive floor.
   The host-only producer design now corrects the seven-module hard dependency
   list with the modular SPMI/SDAM nvmem provider and M31B watchdog floor. Its
   required future sequence is W0 full-closure park, W1 matched Recovery sink,
   then W2 Download positive. Exact LinuxLoader maps `0x01` through RVA
   `0x4aca0` to mode 2 and the explicit Recovery branch. W1 must gate the
   `/soc/reboot_reason` binding under `qcom-reboot-reason`, because Samsung's
   pre-defined Recovery handler does not write the PON value itself. It must
   also prove actual command registration through the mutex-protected
   `sec_reboot_cmd` debugfs list; `sec_qc_rbcmd` registers those handlers on an
   asynchronous worker after platform probe returns. Exact `qcom_scm` and
   `qcom-dload-mode` bindings are also mandatory to keep the clean reboot from
   being confounded with armed dump/RDX state. The 15-module closure must use
   provider-by-provider phase barriers rather than one final poll. W0/W1/W2
   reuse one identical init and differ only by one normalized five-byte mode
   file. See
   `docs/reports/S22PLUS_FYG8_LANE_W_REBOOT_REASON_PRODUCER_CONTROL_DESIGN_2026-07-11.md`.
2. **Lane K - kernel trust/instrumentation:** reproduce an unchanged
   stock-equivalent kernel build, prove static KMI/module compatibility, then
   perform one unpatched rebuilt-kernel viability gate before any
   Magisk-equivalent measurement carrier.
3. Add kernel-side witness changes only as a separately tested hypothesis. A
   rebuild cannot be assumed to fix V3439 retention. S-Boot/reset-path clearing,
   dynamic ramoops placement, and header validity remain unseparated.
4. Change Samsung security configuration only if a specific dependency is
   proven to block a named observation or bring-up step.

Lane W host-only design does not wait for R1. Its independent static review is
complete and the resulting W0/W1/W2 contract is recorded, but current
authorization stops before candidate source or artifact implementation. Any
candidate build, boot flash, or repeated beacon confirmation still needs a
fresh narrow SHA-pinned `AGENTS.md` exception and explicit operator approval.

Do not begin with `CONFIG_RKP=n`, and do not treat
`RKP+KDP+UH+DEFEX+PROCA+FIVE=n` as a community-proven recipe. Mainline ramoops
is also not the default witness target: V3438 proved backend registration and
binding, while V3439 retained zero current-run ramoops records across the
attended SysRq/RDX/reset path.

The known-booting Magisk boot has now been audited byte-for-byte. Its kernel is
the stock kernel plus exactly the Magisk v30.7 DEFEX and PROCA patches (9 changed
bytes in two ranges); RKP and legacy-SAR patch patterns did not match, while
embedded `CONFIG_RKP=y` remains unchanged. Its signed stock vbmeta is copied
unchanged and therefore has a stale payload digest. Report:
`docs/reports/S22PLUS_FYG8_MAGISK_BOOT_SEMANTIC_AUDIT_2026-07-11.md`.

This creates four distinct labels:

- `byte-identical-stock-kernel`: the shipped stock kernel hash;
- `static-stock-equivalent-kernel`: the unpatched R2-GO rebuild;
- `unpatched-rebuilt-kernel-live-viable`: the R2-GO rebuild after a strict
  unpatched live viability proof;
- `magisk-equivalent-kernel`: the R2-GO rebuild plus exactly the v30.7 DEFEX and
  PROCA patches, preserving the known Magisk baseline posture including RKP-on.

The first live rebuild proof uses the unpatched label and cannot require root.
The Magisk-equivalent label is a separate later measurement gate, not the first
proof and not an unchanged-kernel claim. Architecture-review record:
`docs/reports/S22PLUS_FYG8_NATIVE_PID1_PARALLEL_LANES_ARCHITECTURE_REVIEW_2026-07-11.md`.
Exact-build bootloader/reboot-reason correction:
`docs/reports/S22PLUS_FYG8_BOOTLOADER_REBOOT_REASON_AND_RETAINED_MEMORY_STATIC_RE_2026-07-11.md`.

## Pinned Inputs

The exact FYG8 release is an overlay, not a self-contained source archive.
Samsung's FYG8 instructions require the `S906NKSU7FYD9` base followed by the
FYG8 update.

| Input | SHA256 | State |
|---|---|---|
| Base `Kernel.tar.gz` | `86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf` | present |
| Base `Platform.tar.gz` | `c560080a1ed9115fb6f265067d853a52d58c85a829e49d0056f9ce8352f6bdd3` | present; not yet required by kernel build |
| FYG8 delta `S906NKSS7FYG8_kernel.tar.gz` | `23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a` | present and overlaid with one stripped `Kernel/` prefix |
| FYG8 build instructions | `eda4809f02b548a2b2a3d5266dbf03714defba1bf1d11b1ed5113ffc372c7564` | present |

Combined private work tree:
`workspace/private/work/s22plus_fyg8_kernel_rebuild_r0` (approximately 2.9 GiB
before build output).

The build configuration requires Android Clang `r416183b`. The matching AOSP
kernel-build manifest family uses `master-kernel-build-2021` prebuilts.

| Tool repository | Pinned commit |
|---|---|
| `platform/prebuilts/clang/host/linux-x86` | `6e3223f76384455acde43affde3df0ea9df66c0d` |
| `platform/prebuilts/build-tools` | `cfedc16ec3deb680fca6fe2aff44a1837a97b50d` |
| `platform/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8` | `4e6f66acf138d40d9a80be24b275abb9c6eed729` |
| `kernel/prebuilts/build-tools` | `ca5b087f88c0302ff66f59a6f26be663e92baf15` |

Verified compiler identity:

```text
Android (7284624, based on r416183b) clang version 12.0.5
LLVM project c935d99d7cf2016289302412d708641d52d2f7ee
```

## R0 Build Findings

### Confirmed

- The source reaches real GKI compilation with the pinned hermetic toolchain.
- The unchanged Full-LTO configuration compiles the GKI translation units,
  including RKP, KDP, UH, FIVE, PROCA, DEFEX, pstore, and ramoops code.
- A `LTO=thin` diagnostic build completes the GKI link, FIPS HMAC update, KMI
  symbol-list comparison, and produces `Image`, `Image.lz4`, `vmlinux`,
  `System.map`, and `vmlinux.symvers` for release `5.10.226-android12-9`.
- The ThinLTO diagnostic then compiles the Qualcomm/Samsung vendor tree and its
  hardware modules through final module LTO and modpost.

The following hashes pin that host diagnostic only. These files are non-stock
ThinLTO evidence and are explicitly not boot or flash candidates.

| Diagnostic output | SHA256 |
|---|---|
| GKI `Image` | `54fdf281f50b744d0a0b9f3501eefe912f8143f0eced870f2e9035f74f9cf9ab` |
| GKI `Image.lz4` | `9d7055481cfdb7aa8de861f565527a1b044df103572335f471de94a8f2973e52` |
| GKI `vmlinux` | `ef44b3d919a7d62e18742d1ef30c14b5b4a32e0a96d8cc0fa5bbb0c67364f6f2` |
| GKI `System.map` | `d7f2f55000d839b1ee433059d6346c470fcb105a27d17ad723004a91489a15a5` |
| GKI `vmlinux.symvers` | `4d8173123233e67c2d7d00e0ed18f37597aafaf5a98681892722e7eb765e2051` |
| Generated GKI `.config` | `cc775bca9cba24dcb14ba5dcc4335b03e1f219c85b8ddcd70425d146deb80175` |

### Blockers found

1. **Stock Full-LTO host resource floor.** On this 16 GiB host, `ld.lld` reached
   about 12.5 GiB RSS while system swap reached about 14 GiB. It entered sustained
   swap wait, so the run was stopped before host stability degraded. This is an
   environment limit, not a compiler error. Stock-equivalent build PASS remains
   open until Full LTO completes on a controlled nominal 32 GiB physical-memory
   setup. Swap is recommended headroom, not a substitute for that physical RAM.
2. **Samsung helper typo.** The supplied `build_kernel_GKI.sh` and README contain
   `export TARGET_BUILD_VARIANT= user`. In shell this exports an empty value. The
   build consequently asks for nonexistent
   `arch/arm64/configs/vendor/waipio_sec__defconfig`. A wrapper must set exactly
   `TARGET_BUILD_VARIANT=user` without modifying kernel source.
3. **ThinLTO is not source-compatible with one Samsung arm64 panic wrapper.** The
   vendor diagnostic reaches modpost and fails on
   `__sec_arm64_ap_context_on_panic` from
   `sec_arm64_ap_context.ko`. The symbol is a static C function referenced by a
   literal `bl` inside naked inline assembly. ThinLTO does not preserve that
   relationship for modpost. This does not prove a Full-LTO failure and is one
   reason ThinLTO output must never be called stock-equivalent.
4. **Defconfig normalization is not clean.** The supplied GKI defconfig produces
   a nonempty `savedefconfig` delta. The build script warns but continues. The
   exact generated `.config` must be compared against the running FYG8 IKCONFIG;
   source-file intent alone is insufficient.
5. **Build provenance timestamp is not yet pinned.** Samsung's archive has no
   nested Git history. Because the work tree currently lives below this repo,
   AOSP's `git -C` timestamp lookup can inherit the parent repository commit.
   A wrapper must explicitly pin `SOURCE_DATE_EPOCH`/build metadata from stock
   evidence or build outside any unrelated parent Git worktree.

## Gated Roadmap

### R0 - Reproducible host build environment

Status: **PASS; DEBIAN 13 32 GiB BUILD HOST REPRODUCED**

- Generate the combined source tree deterministically from pinned archives.
- Verify every FYG8 delta member after stripping exactly one `Kernel/` prefix.
- Use a wrapper that exports `TARGET_BUILD_VARIANT=user` and all documented
  `g0q_kor_singlex` variables.
- Pin AOSP prebuilt commits and compiler identity.
- Isolate build metadata from the parent Git repository.
- Record peak RAM, swap, elapsed time, config hash, and all output hashes.

Exit gate: one source-generation audit plus one non-stock smoke build reaches
all intended code paths without an unexplained missing input. Smoke output is
never flashable.

2026-07-11 host-audit close:

- 166,037 reconstructed source members match the resident tree exactly;
- the 51-member FYG8 delta changes 22 and re-ships 29 identical base files;
- the stock ARM64 Image exposes exact release/compiler metadata and embedded
  IKCONFIG SHA256
  `99352a4f8db49814330c9d2c28038fafbbd1dadbe1fef3082c6d7e2614c2dbf1`;
- stock versus ThinLTO diagnostic config differs only in Full/Thin LTO and the
  host-specific absolute `UNUSED_KSYMS_WHITELIST` path;
- the existing 441-module map now records 22,131 consumer-side symbol CRC
  requirements covering 4,060 unique symbols;
- current-host Full-LTO preflight fails closed only on physical RAM, while all
  source, compiler, prebuilt-commit, provenance, and disk gates pass;
- a private 20-file/four-repository transfer manifest is ready for the
  Debian 13 FX-8300 32 GiB build host; toolchain transfer preserves `.git`
  metadata, and preflight requires Git plus GNU `/usr/bin/time`. Swap is
  recommended headroom, not a hard rejection when physical RAM passes.

Report:
`docs/reports/S22PLUS_FYG8_KERNEL_REBUILD_R0_HOST_AUDIT_2026-07-11.md`.

### R1 - Unchanged stock Full-LTO build

Status: **R1 V3 CLEAN FULL-LTO REPRODUCIBILITY PASS 2026-07-12**

- Use the supplied config with Full LTO; no security or witness changes.
- Require every artifact owned by the pinned build rules: kernel Image form,
  `vmlinux`, `System.map`, generated `.config`, symvers output, and generated
  modules/DTBs only when the tree actually emits them.
- Treat stock DTBO, `vendor_boot`, `init_boot`, and vendor ramdisk as pinned
  inputs unless the R1 build rules explicitly generate them. Repacked boot and
  Odin containers are later derived packages, not R1 outputs.
- Bind source-tree and overlay hashes into preflight, reject an unpinned ambient
  tool environment, and persist complete tool/version and resource evidence.
- Complete GKI, Qualcomm/Samsung vendor modules, external modules, KMI checks,
  FIPS update, and the build-owned dist copy.
- Treat missing modules, unresolved symbols, KMI failures, or generated-config
  drift as FAIL, not as warnings to waive.

Exit gate: complete provenance-bound Full-LTO build with every build-owned
artifact present, typed, hashed, and no unresolved failure. This proves
buildability only, not device compatibility or stock equivalence.

2026-07-11 gate implementation:

- build schema v2 reruns the content-addressed FYD9+FYG8 overlay audit during
  every preflight and requires all 166,037 resident members to match;
- ambient `CC`, flags, hooks, and parent PATH state are not inherited;
- zero build return with a missing Image/vmlinux/System.map/config/symvers/
  modules.builtin metadata or with zero generated modules is FAIL;
- generated `.ko` and every `Module.symvers`/`vmlinux.symvers` file are hashed
  into the R1 result;
- exact current-host Full-LTO preflight passes every non-resource gate and
  refuses only the 15.2 GiB physical-memory host.

2026-07-12 remote close:

- Debian 13 FX-8300 host preflight passed with 33,662,164,992 bytes RAM;
- the clean Full-LTO compile completed all eight core outputs in 33:15 with
  peak RSS 24,252,992 KiB and zero swap;
- bounded host-tool/dist fixes preserved all eight output hashes exactly;
- final R1 returned zero with provider closure PASS, 2,397 generated `.ko`
  paths, and 15 symvers files;
- R1 result SHA256 is
  `027d0104ea0640b4d7faca1607dcaae4d0b1bb6af403725c9bd85e524f54b18f`.

2026-07-12 correction: the result above proves Full-LTO buildability but is an
R1 v2 historical result, not the final reproducible R1. Its `Image` banner uses
the live compile timestamp `Sun Jul 12 07:16:46 UTC 2026`, while stock requires
`Fri Aug 1 05:55:56 UTC 2025`. R1 v3 must pass the temporary Samsung setup-env
timestamp-control gate and exact stock banner before reproducibility closes.

2026-07-12 final clean R1 v3 close:

- a separately reconstructed source tree passed all 166,037 member checks;
- Full-LTO completed in 33:47.58 with peak RSS 24,252,508 KiB and zero swaps;
- exact 398-byte FYG8 banner equality and timestamp apply/restore passed;
- all eight outputs, 2,397 generated modules, both provider closures, and all
  15 symvers path identities passed;
- unpatched Image SHA256 is
  `9110a7722f28f075c5cb09789710341b44956147fa05867d05e5b3e7d024770d`;
- R1 v3 result SHA256 is
  `448f024b9c0d99fcac02cbc6a858a227ca5cb290a44f0616621542994b329c6f`.

### R2 - Static stock-equivalence audit

Status: **R2 V2 STATIC EQUIVALENCE PASS 2026-07-12**

- Compare generated kernel release and version metadata with running FYG8.
- Compare generated `.config` with captured running IKCONFIG.
- Close the full on-disk module union across vendor ramdisk, `vendor_dlkm`,
  `system_dlkm`, other mounted module sources, and `modules.builtin`. The 441
  first-stage files are a subset, not the compatibility corpus.
- Compare KMI symbol CRCs, generated symvers, exported symbol surface, module
  `vermagic`, and consumed-symbol closure against that declared shipped union.
- Identify modules by normalized name, `srcversion`, `vermagic`, and
  decompressed content hash; resolve built-ins separately.
- Keep runtime loaded-set parity as a later live check against a pinned baseline
  captured at the same boot milestone and workload. The P0 count of 482 is not
  a universal must-load count.
- Compare Image format, load size, boot-image capacity, compression, and Samsung
  boot container invariants.
- Explain every residual difference; no unexplained delta advances.

Exit gate: static compatibility report says GO for one unchanged boot candidate.

2026-07-11 corpus close and diagnostic:

- exact LP geometry/header/table checksums pass for raw FYG8 `super.img`;
- partition set is exactly `system`, `odm`, `product`, `system_ext`, `vendor`,
  and `vendor_dlkm`; there is no `system_dlkm` or `odm_dlkm` partition;
- recursive F2FS walks find zero `.ko` under `system`, `vendor`, and `odm`;
- `vendor_dlkm` has 356 modules; overlap with vendor ramdisk is 306/306
  byte-identical after F2FS LZ4-cluster reconstruction;
- 50 vendor_dlkm-only plus 135 vendor-ramdisk-only modules produce a complete
  491-name on-disk union;
- the combined consumer contract is 25,864 rows and 4,619 unique symbols;
- the old ThinLTO diagnostic matches 22,600 rows, has zero mismatched CRCs,
  and misses 3,264 module-provider rows because vendor modpost did not finish;
- `s22plus_fyg8_kernel_r2_audit.py` now requires the pinned complete-corpus
  layout plus a schema-v3 Full-LTO R1 PASS and exact stock banner before it can
  return R2 v2 PASS.

Report:
`docs/reports/S22PLUS_FYG8_KERNEL_REBUILD_R1_R2_HOST_GATES_2026-07-11.md`.

2026-07-12 R2 close:

- exact FYG8 release/compiler and Full-LTO config gates pass;
- the only config delta is the allowlisted absolute unused-symbol whitelist
  path;
- all 25,864 consumer CRC rows close against 10,511 provider symbols;
- missing, mismatched, and conflicting CRC counts are all zero;
- R2 result SHA256 is
  `66c76073881752752c8a0eeddee03e8d6f8d63dc84109441616eda7386dea4cf`.

2026-07-12 correction: R2 v1 verified release/compiler substrings but not the
full Linux banner and therefore accepted the non-stock build timestamp above.
R2 v2 requires exact equality with the pinned FYG8 `linux_banner` and an R1 v3
result whose timestamp-control script was restored. The old R2 hash is
historical evidence and does not satisfy the current R3 prerequisite.

2026-07-12 final R2 v2 close:

- exact banner/release/compiler/PREEMPT and Full-LTO config gates pass;
- 25,864/25,864 consumer CRC rows close over 4,619 required symbols against
  10,511 providers, with zero missing, mismatched, or conflicting symbols;
- complete 491-module corpus and boot-capacity gates pass;
- R2 v2 result SHA256 is
  `ee935a523270b45c93d2db3e1f21d32b2bf49f3a96965efe5d8df66515964392`.

### R3 - Unpatched rebuilt-kernel boot-only viability proof

Status: **CARRIER DESIGN CORRECTED AND R1 V3/R2 V2 CLOSED 2026-07-12; BLOCKED
ON STATIC-CHECKER IMPLEMENTATION, TWO-RUNG ARTIFACTS, FRESH POLICY, AND
OPERATOR APPROVAL**

- Exact-stock analysis found a 528-byte Samsung `SignerVer02` record that
  MagiskBoot v30.7 normalizes to a 16-byte marker; no-change exact-stock repack
  is therefore source-confirmed non-identical.
- R3C0 first proves the normalized carrier with the exact stock kernel and
  stock ramdisk, then rolls back in its own one-shot session.
- Only after R3C0 PASS may R3C1 start from byte-identical R3C0 bytes and replace
  only the kernel region with the unpatched R2-GO
  `static-stock-equivalent-kernel`.
- Make no DEFEX, PROCA, RKP, legacy-SAR, security-config, ramdisk, or witness
  change.
- Explicitly record that copied signed vbmeta has a stale boot-payload digest
  and that this path relies on the already-unlocked bootloader behavior.
- AP must contain only `boot.img.lz4` and satisfy all existing boot-only safety
  and rollback pins.
- Require a fresh SHA-pinned `AGENTS.md` one-shot exception and explicit operator
  approval. This roadmap grants no live authorization.
- PASS requires only the predeclared host-visible normal Android milestone,
  bounded hardware identity available without root, and exact boot-only
  rollback readiness. Root is not a gate.
- Normal Android boot proves a kernel-viability bit, not complete module ABI
  closure or native PID1.
- Restore the pinned known-booting Magisk boot after proof, even on PASS.

Exit gate: R3C0 proves and rolls back the normalized stock carrier, then a
separate R3C1 run proves and rolls back the unpatched R2-GO rebuild. This proves
only that the rebuilt kernel can boot this hardware far enough for the selected
milestone after its carrier path is independently controlled.

Host-only artifact, static-gate, live-milestone, rollback, classification, and
timeline design:
`docs/plans/S22PLUS_FYG8_R3_UNPATCHED_KERNEL_VIABILITY_DESIGN_2026-07-12.md`.
No candidate artifact was generated by that design unit.
Correcting carrier audit:
`docs/reports/S22PLUS_FYG8_R3_CARRIER_AND_STATIC_CHECKER_AUDIT_2026-07-12.md`.

### R3B - Optional Magisk-equivalent measurement carrier

Status: **PENDING R3, NEED, AND FRESH POLICY**

- Enter only when rooted measurement on the rebuilt kernel is needed.
- Locate DEFEX and PROCA targets by audited content and semantics, never stale
  offsets. Require one approved target per patch; zero or multiple candidates
  are FAIL.
- Re-audit against the rebuilt-unpatched kernel and require only the intended
  two patch ranges. Any additional change is FAIL.
- Preserve and re-audit the pinned Magisk ramdisk semantics.
- Keep RKP and legacy-SAR no-op results explicit and preserve copied-vbmeta
  caveats.

Exit gate: one separately labeled `magisk-equivalent-kernel` provides the
predeclared rooted measurements and rolls back cleanly. This is not an
unchanged-kernel or native-PID1 proof.

### R4 - Minimal kernel-side witness hypothesis

Status: **PENDING R3; REBOOT-REASON PRODUCER HOST DESIGN PROCEEDS IN PARALLEL**

- Keep all Samsung security configs unchanged.
- Add one bounded marker at a selected kernel/init boundary.
- Prefer the already proven Samsung retained/sec_debug channel or instrument the
  exact reset path. Do not assume mainline ramoops retention is repaired by a
  rebuild.
- Prove the marker under stock Android first, then use it to discriminate direct
  PID1 execution.

Exit gate: a current-run marker survives the selected failure/reset path and is
recoverable after rollback.

### R5 - Security dependency experiment

Status: **DEFERRED; NOT AUTOMATIC**

- Enter only if R4 fails with evidence that RKP/KDP/UH blocks the exact patch or
  call path.
- Derive the smallest coherent config/code dependency set from local source.
- Do not disable DEFEX, PROCA, or FIVE merely because unrelated KernelSU builds
  did so.
- Each config change needs a static dependency report, new build hashes, a fresh
  boot-only gate, and the same rollback contract.

Exit gate: one isolated dependency hypothesis is confirmed or retired.

### R6 - Native PID1 and Debian continuation

Status: **LANE W PRODUCER/CONTROL DESIGN ACTIVE; RICH BRING-UP PENDING A RELIABLE WITNESS**

First prove that native PID1 can load and bind the exact Samsung reboot-command
and PON-writer dependency closure, and distinguish `reboot("download")` from a
generic reset control. Only then may Download be used to raise a positive
direct-PID1 floor. Rich USB, display, storage, and Debian bring-up remain
downstream of a witness that can distinguish early userspace progress and
reset reason.

## Stop Rules

- No kernel build output is flashable before R2 GO and a fresh R3 policy.
- Lane W authorizes host-only producer/control and checkpoint design only; it
  grants no candidate build, flash, or repeated beacon run.
- No security config bundle is accepted from forum prose alone.
- No ramoops repetition is justified by merely rebuilding the same enabled
  backend.
- A smoke build with `LTO=none` or `LTO=thin` cannot satisfy R1 or R2.
- Any boot candidate remains boot-partition-only and uses the pinned rollback
  envelope. All other partition writes remain forbidden.
