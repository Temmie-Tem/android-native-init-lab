# S22+ FYG8 Kernel Rebuild Roadmap

Date: 2026-07-11 KST
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`
Scope: host-only planning and build validation; no device contact or flash

## Decision

An FYG8-derived kernel rebuild is a viable research branch, but it is not yet a
proven boot path and is not a guaranteed retained-witness solution. The active
order is:

1. reproduce an unchanged stock-equivalent kernel build;
2. prove static compatibility with the running FYG8 kernel and vendor modules;
3. prove one boot-only stock-equivalent candidate with mandatory rollback;
4. add one minimal observation change;
5. change Samsung security configuration only if a specific dependency is
   proven to block that observation change.

Do not begin with `CONFIG_RKP=n`, and do not treat
`RKP+KDP+UH+DEFEX+PROCA+FIVE=n` as a community-proven recipe. Mainline ramoops
is also not the default witness target: V3438 proved backend registration and
binding, while V3439 retained zero current-run ramoops records across the
attended SysRq/RDX/reset path.

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

Status: **HOST AUDIT PASS; 32 GiB BUILD-HOST REPRODUCTION PENDING**

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
- a private nine-file/four-repository transfer manifest is ready for the
  Debian 12 FX-8300 32 GiB build host; toolchain transfer preserves `.git`
  metadata, and preflight requires Git plus GNU `/usr/bin/time`. Swap is
  recommended headroom, not a hard rejection when physical RAM passes.

Report:
`docs/reports/S22PLUS_FYG8_KERNEL_REBUILD_R0_HOST_AUDIT_2026-07-11.md`.

### R1 - Unchanged stock Full-LTO build

Status: **BLOCKED ON CONTROLLED BUILD MEMORY AND R0 WRAPPER**

- Use the supplied config with Full LTO; no security or witness changes.
- Complete GKI, Qualcomm/Samsung vendor modules, external modules, DTBs, KMI
  checks, FIPS update, and dist copy.
- Treat missing modules, unresolved symbols, KMI failures, or generated-config
  drift as FAIL, not as warnings to waive.

Exit gate: complete Full-LTO dist with hashes and zero unresolved build failure.
This proves buildability only, not device compatibility.

### R2 - Static stock-equivalence audit

Status: **PENDING R1**

- Compare generated kernel release and version metadata with running FYG8.
- Compare generated `.config` with captured running IKCONFIG.
- Compare KMI symbol CRCs, generated `vmlinux.symvers`, exported symbol surface,
  module `vermagic`, and required-symbol closure against the exact shipped
  modules.
- Compare Image format, load size, boot-image capacity, compression, and Samsung
  boot container invariants.
- Explain every residual difference; no unexplained delta advances.

Exit gate: static compatibility report says GO for one unchanged boot candidate.

### R3 - Stock-equivalent boot-only proof

Status: **PENDING R2 AND FRESH POLICY**

- Build from the known-booting Magisk boot base while replacing only the kernel
  payload required by the selected boot format.
- AP must contain only `boot.img.lz4` and satisfy all existing boot-only safety
  and rollback pins.
- Require a fresh SHA-pinned `AGENTS.md` one-shot exception and explicit operator
  approval. This roadmap grants no live authorization.
- PASS requires Android, Magisk root, exact hardware identity, required vendor
  modules, USB, display, storage, and rollback readiness.
- Restore the pinned known-booting Magisk boot after proof, even on PASS.

Exit gate: one unchanged rebuilt kernel boots and rolls back cleanly.

### R4 - Minimal witness kernel

Status: **PENDING R3**

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

Status: **PENDING R4 WITNESS**

Resume direct native PID1 only after the witness can distinguish kernel entry,
`/init` entry, early userspace progress, and reset reason. USB, display, and
Debian bring-up remain downstream of that observation boundary.

## Stop Rules

- No kernel build output is flashable before R2 GO and a fresh R3 policy.
- No security config bundle is accepted from forum prose alone.
- No ramoops repetition is justified by merely rebuilding the same enabled
  backend.
- A smoke build with `LTO=none` or `LTO=thin` cannot satisfy R1 or R2.
- Any boot candidate remains boot-partition-only and uses the pinned rollback
  envelope. All other partition writes remain forbidden.
