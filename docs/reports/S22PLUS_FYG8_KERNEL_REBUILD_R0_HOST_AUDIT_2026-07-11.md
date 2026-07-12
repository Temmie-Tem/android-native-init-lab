# S22+ FYG8 Kernel Rebuild R0 Host Audit

Date: 2026-07-11 KST
Target: `SM-S906N/g0q/S906NKSS7FYG8`
Scope: host-only source, toolchain, stock-kernel, and shipped-module audit

## Verdict

**R0 host audit PASS; reproduction on the 32 GiB build host remains pending.**

The pinned FYD9 base plus FYG8 delta reconstructs the resident source tree
exactly. The stock boot kernel supplies an extractable IKCONFIG and an exact
module ABI baseline. A fail-closed build wrapper now fixes Samsung's empty
`TARGET_BUILD_VARIANT`, isolates the source from the parent Git repository,
pins stock build metadata and release suffix, verifies all four toolchain
repositories, and refuses Full LTO on the current 16 GiB host. Preflight also
requires Git and Debian's GNU `time` package so a missing `/usr/bin/time` cannot
fail after an otherwise green gate.

This is not R1. No Full-LTO build completed in this unit, no boot image was
packaged, and no device or USB path was contacted.

## Source Overlay

Checked tool:
`workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_overlay_audit.py`

Result from content-addressed reconstruction of both pinned archives:

| Metric | Result |
|---|---:|
| FYD9 base members | 166,037 |
| FYG8 delta members after exact `Kernel/` strip | 51 |
| Added | 0 |
| Replaced, changed | 22 |
| Replaced, byte-identical | 29 |
| Final members | 166,037 |
| Resident missing/mismatched | 0 / 0 |
| Base absolute symlinks, safely recorded | 5 |

Every archive member path and link ancestor was validated before hashing. The
official base contains five absolute symlinks; they are recorded without
dereference, and the archive contains no member below a link ancestor. The
resident tree matches all reconstructed members exactly. A tar overlay cannot
express a deletion, so `deletion_detectable=false` remains an explicit limit.

Private manifest SHA256:
`678934134cd199fbf1792ba298ce0adf8acb4ffb2660fca7c923a2e63055ae7b`.

## Stock Kernel Baseline

Checked tool:
`workspace/public/src/scripts/revalidation/s22plus_fyg8_stock_kernel_baseline.py`

- Stock boot SHA256:
  `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`.
- Stock kernel payload SHA256:
  `027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d`.
- Android boot header: version 4, 4096-byte alignment, 4096-byte signature.
- Kernel payload: uncompressed ARM64 Image.
- Release:
  `5.10.226-android12-9-30958166-abS906NKSS7FYG8`.
- Compiler: Android Clang 12.0.5 based on `r416183b`.
- Embedded IKCONFIG SHA256:
  `99352a4f8db49814330c9d2c28038fafbbd1dadbe1fef3082c6d7e2614c2dbf1`.
- Stock IKCONFIG proves Full LTO, MODVERSIONS, IKCONFIG/IKCONFIG_PROC, and 4 KiB
  arm64 pages.

Comparison against the current non-stock ThinLTO diagnostic `.config` has
exactly three differences:

```text
LTO_CLANG_FULL y -> n
LTO_CLANG_THIN n -> y
UNUSED_KSYMS_WHITELIST <Samsung build path> -> <local build path>
```

The absolute whitelist path is build-host provenance. The Full/Thin difference
is expected and is why the diagnostic output cannot satisfy R1 or R2.

## Build Wrapper

Checked tool:
`workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_build.py`

The wrapper pins:

- `TARGET_BUILD_VARIANT=user`;
- `LOCALVERSION=-30958166-abS906NKSS7FYG8`; Samsung's
  `setlocalversion` supplies `-android12-9` and target configs supply optional
  values such as `-gki`, while `BUILD_NUMBER` stays unset to avoid an extra
  `-ab30958166` suffix;
- `SOURCE_DATE_EPOCH=1754027756` and stock timestamp/user/host;
- `GIT_CEILING_DIRECTORIES` above the isolated source tree;
- an isolated host-tool override exposes only GNU `tar` and GNU `xargs`,
  because the pinned Android Toybox applets lack the `--transform` and `-L`
  options used by the pinned build scripts;
- `ANDROID_KERNEL_OUT` stays below the generated `out/` tree and
  `ANDROID_PRODUCT_OUT` remains unset, so this kernel-only source kit does not
  enter the unavailable full-Android `bionic/system` export branch;
- exact Clang and three AOSP build-prebuilt commits;
- Full LTO and explicit job count.

Current-host preflight passed every source, toolchain, compiler, provenance,
and disk gate, then refused execution because physical memory is 15.2 GiB,
below the nominal 32 GiB Full-LTO floor. This is the intended result. The
wrapper never packages a boot image and always emits
`stock_equivalent_claim=false`; R2 and R3 remain separate gates.

## Shipped Module ABI

The existing FYG8 module map was extended rather than duplicated:
`workspace/public/src/scripts/revalidation/s22plus_fyg8_module_map.py`.

- Authoritative vendor-ramdisk module set: 441 exact `.ko` files.
- Expected vermagic:
  `5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8 SMP preempt mod_unload modversions aarch64`.
- Consumer-side required symbol/CRC rows: 22,131.
- Unique required symbols: 4,060.
- CRC map:
  `docs/module-map/s22plus-fyg8/symbol-crc-requirements.tsv`.
- CRC map SHA256:
  `9be63bf9d2086d0823cc2b87cc2412b34f3d44394444c0cb693a5b1edf5a6e86`.

These CRCs prove only what shipped modules require. Provider compatibility is
unproved until the completed Full-LTO `vmlinux.symvers` and rebuilt module set
are compared against them.

## Build-Host Transfer

`s22plus_fyg8_kernel_transfer_manifest.py` emitted a private manifest covering
nine pinned files and four clean AOSP repository commits. The file set includes
`AGENTS.md` and `GOAL.md`, which are required root markers for standalone tool
execution. Toolchain transfers
must preserve complete Git checkout metadata because commit and dirty-state
verification are hard gates. The recipe transfers the two source archives plus
tools, then reconstructs the source on the build host instead of copying the
current 10 GiB generated tree.

Host floor recorded in the manifest:

- Debian 13 x86_64;
- at least 30 GiB visible physical RAM, representing nominal 32 GiB;
- 8 GiB swap recommended as non-blocking headroom;
- at least 30 GiB free disk;
- `-j8` on the FX-8300 host;
- Debian packages `git` and `time`.

## Next Gate

1. Reconstruct the source from pinned archives on the 32 GiB FX-8300 host.
2. Run the overlay audit and require exact PASS.
3. Run Full-LTO preflight and require all toolchain/resource/provenance gates.
4. Execute R1 Full LTO under `tmux` with `/usr/bin/time -v` evidence.
5. Return the complete dist and logs for R2 static comparison.

No artifact from this unit is flashable, and this report grants no live
authorization.
