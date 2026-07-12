# S22+ FYG8 R4W1 Host Build And Reproducibility

Date: 2026-07-13 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `PASS_R4W1_CLEAN_REPRODUCIBILITY`

This is a host-only R4W1 build-influence and reproducibility report. No device
contact, transfer, reboot, flash, or partition write occurred. Samsung's build
pipeline did generate generic host-side `boot.img`, `vendor_boot.img`,
`dtbo.img`, `vendor_dlkm.img`, and `super.img` side outputs. They are not
promoted as live candidates and are not authorized for flashing.

## Witness Contract

Patch SHA256:
`e66962c9e8cc503f9c5e94265816fdc2e96f4920a2d47387c6f1a4d9bbc6b787`.

The patch changes only GKI `init/main.c`, `init/Kconfig`, and
`gki_defconfig`. The only semantic config delta is
`CONFIG_S22PLUS_FYG8_RETAINED_WITNESS=y`; RKP, KDP, UH, DEFEX, PROCA, FIVE,
module signing, KMI, and Full-LTO settings remain unchanged.

After `kernel_execve("/init")` returns zero for PID 1, the witness validates
Samsung ring magic `0x4d474f4c` and appends this 94-byte marker to the existing
`0x800200000` / `0x200000` `sec_log_buf` circular payload:

```text
[[S22R4W1|id=9ed5923b08c5eedbbdb0aaa6f6a5200c|phase=RAMDISK_EXEC_ACCEPTED|pid=1|path=/init]]
```

Invalid magic is fail-open for boot and leaves the ring unchanged. The patch
contains no panic, reset, filesystem, block, partition, security-setting, or
device-control operation.

All eleven FYG8 g0q DT revisions bind `samsung,kernel_log_buf` to the same
direct-mapped carveout. The checker rejects `no-map`. The final static gate
requires vendor `CONFIG_SEC_LOG_BUF=m` and a regular built
`sec_log_buf.ko`, proving that vendor writer registration follows the early
kernel witness.

## External Standards Cross-Check

The local controls were checked against primary documentation:

- Linux kernel reproducible-build documentation:
  <https://docs.kernel.org/kbuild/reproducible-builds.html>
  - pin `KBUILD_BUILD_TIMESTAMP`, `KBUILD_BUILD_USER`, and
    `KBUILD_BUILD_HOST`;
  - use `-fdebug-prefix-map` in both `KCFLAGS` and `KAFLAGS` for
    out-of-tree C and assembly paths;
  - normalize IKHEADERS timestamps;
  - control module-signing keys, RANDSTRUCT seeds, VDSO salt, and Git-derived
    localversion when those features are active.
- Android kernel build documentation:
  <https://source.android.com/docs/setup/build/building-kernels>
  - legacy `build.sh` is the correct AOSP flow for Android 12 branches;
  - Android 14 and newer use Kleaf instead, so migration is not appropriate for
    this FYG8 `android12-5.10` source tree.
- AOSP Android 12 `build.sh`:
  <https://android.googlesource.com/kernel/build/+/refs/tags/android-12.0.0_r0.40/build.sh>
  - Full LTO is the release-equivalent optimized mode and is explicitly slow;
  - ThinLTO/fast build is appropriate for local iteration but not final FYG8
    equivalence evidence.
- Android stable KMI and ABI monitoring:
  <https://source.android.com/docs/core/architecture/kernel/stable-kmi> and
  <https://source.android.com/docs/core/architecture/kernel/abi-monitor>
  - use one exact `gki_defconfig`, the matching LLVM toolchain, symbol lists,
    `CONFIG_MODVERSIONS` CRCs, and a generated ABI representation;
  - vendor modules and GKI must remain KMI-compatible.
- Samsung Open Source Release Center:
  <https://opensource.samsung.com/>
  - the public site distributes source but does not expose an indexed FYG8
    per-device build guide;
  - the operative Samsung/Qualcomm instructions for this release are therefore
    the supplied `prepare_vendor.sh`, `build.sh`, and
    `build.config.msm.{waipio,gki}` files in the exact source package.

## Build Influence Matrix

| Axis | Local state | Effect on final raw GKI `Image` |
| --- | --- | --- |
| source membership | base/delta archives and 166,037-member reconstructed tree are SHA-pinned | direct |
| config | exact stock config plus one witness config; whitelist path normalized | direct |
| timestamp/user/host/version | fixed epoch, FYG8 timestamp, `build-user`, `build-host`, build version 1 | direct banner/kheaders |
| Git/localversion | parent Git discovery blocked by `GIT_CEILING_DIRECTORIES`; exact release gate | direct release string |
| LLVM toolchain | exact Clang repo commit and identity; Full LTO | direct code/link |
| host tools | 17 effective executables now recorded by resolved SHA/size | direct or generated metadata; same-host scope |
| parallel `-j8` | fixed Makefile input order; `llvm-ar cDPrST`; E/F archives and initcall/symversion scripts identical | timing only after deterministic ordering |
| Full LTO | dominant serial link, about 24 GiB peak RSS; E/F runtime bytes stable | direct |
| absolute paths | KMI config, VDSO source/out paths, and global objtree DWARF paths controlled separately | direct through embedded data/build-id |
| KALLSYMS | address-sorted multipass generation plus final `System.map` consistency check | direct |
| VDSO | 64/32-bit C and assembly debug paths mapped to stable roots | direct embedded VDSO build-ids |
| IKHEADERS | enabled; sorted tar members, fixed mtime/owner/mode, stable relative config path | direct embedded archive |
| FIPS post-link | symbol/address inputs sorted; fixed SHA256 HMAC key; C/D/E/F HMAC identical | direct 32-byte HMAC |
| module signing | `CONFIG_MODULE_SIG` disabled | inactive |
| RANDSTRUCT | absent/disabled | inactive |
| BTF | disabled | inactive |
| embedded initramfs | `CONFIG_INITRAMFS_SOURCE=""` | inactive in raw Image |
| KMI CRC | all exported symbol/CRC mappings and module consumers checked | vendor-module compatibility |
| ABI type graph | generated `abi.xml` now mandatory and compared to baseline | vendor-module compatibility |
| DTB/DTBO/vendor modules | built outside raw GKI Image | no reverse effect on Image; live bundle concern |
| boot/vendor/super packaging | generated after Image | no reverse effect on Image; not promoted |

The effective tool manifest covers `bash`, `make`, `tar`, `xargs`,
`xz`, `cpio`, `perl`, `python3`, `find`, `sort`, LLVM linker/binutils,
`dtc`, and `depmod`. It proves the final two runs use identical executable
files. It does not prove cross-distribution libc/kernel equivalence; the final
claim remains same-host reproducibility.

## Negative Controls

### A/B: KMI Whitelist Path

The first two successful Full-LTO Images differed because
`CONFIG_UNUSED_KSYMS_WHITELIST` embedded absolute work-tree paths in
`autoconf.h` and IKHEADERS. `System.map` and `vmlinux.symvers` were
already identical. The build harness now changes the one checked Samsung
`build.sh` assignment to a stable relative path and restores exact bytes,
mode, and mtime after the build.

### C/D: VDSO Build Paths

C/D fixed the KMI path and produced identical config, kheaders,
`System.map`, `vmlinux.symvers`, and `abi.xml`, but their Images differed
in three 20-byte ranges: VDSO64 build-id, VDSO32 build-id, and the top-level
kernel build-id derived from those inputs.

The final harness maps `abs_srctree` to `/kernel-src` and `abs_objtree`
to `/kernel-out` in both VDSO makefiles. Independent object relinks produced
stable VDSO64 build-id
`a8d67413f508eece79379340ffc2ab39d2683261` and VDSO32 build-id
`a7c0010c6cc45d42eb5efd74ded7892bb2518c39`.

### E/F: Global Kernel DWARF Path

E/F fixed both earlier issues. Their raw Images were the same size and differed
in exactly one 20-byte range:

- offset: `0x22559f8..0x2255a0b`;
- E kernel build-id: `a49dff40ca66c4f879e0924b8aba6ac7e2bf299f`;
- F kernel build-id: `6539aa60a72e35072a0bec98b538132f24e3b17c`;
- E Image SHA256:
  `7006795392f156af079df0931a8206a9bcc2d323c4d913da2a8b2831b50340ac`;
- F Image SHA256:
  `c3ecf37f590a647cad72b9f2fac72925a22f4e4a60e97782f4df06a52550406f`.

Their `System.map`, `vmlinux.symvers`, `abi.xml`, kheaders, FIPS HMAC,
VDSO build-ids, built-in archives, initcall order, and symversion inputs were
identical. A same-toolchain minimal experiment proved that differing DWARF
compilation directories alone change LLD SHA1 build-id while stripped runtime
bytes remain identical.

The global GKI Makefile control added in `dcbcf091` maps
`abs_objtree -> /kernel-out` for both KBUILD CFLAGS and AFLAGS. A no-build
Kbuild variable probe proved both actual expanded flag sets contain the exact
map, and the source Makefile is restored exactly.

E elapsed `37:31.57`; F elapsed `37:40.73`. Peak RSS was approximately
23.12 GiB. F build result SHA256 is
`bd97cdc2782db20c46f994f2401144e5643415c7981e3b78e1006f9df3c83076`.

## F Post-Build Taint

After F completed, an attempted `make -n` flag probe entered a recursive
Kconfig sync without `ARCH=arm64` and rewrote F's live out-tree `.config`
as x86. It did not rebuild or alter the already-generated Image, maps,
`abi.xml`, kheaders, source files, or result JSON. The completed result JSON
records the original arm64 config SHA256
`9c54c862ac5b6a7f1c29a89041eb027458bc0c1189243bce99cd9ed0eba39efc`.

The F out tree is nevertheless tainted and is permanently excluded from
artifact binding. Its immutable negative-control files and result directory
were copied to private evidence. Future final trees must not receive any make
invocation after result emission; variable expansion probes run before the
build or on a disposable tree only.

## Host Packaging Side Outputs

F generated these non-promoted host artifacts:

| Artifact | SHA256 |
| --- | --- |
| `boot.img` | `b053e90d2dbad848a5f4fe0340cfa3e008aaec0e3d243ba835d1a1b89935c19f` |
| `dtbo.img` | `97639a5856c124d5a9a088c5b5c1e6b66b6b4b23fd423d1046bc5fdb00c2e8f0` |
| `super.img` | `ebcb401f5aa9b534853783203d95aa95cf97b305aa48eee9b3b2729806f56c7a` |
| `vendor_boot.img` | `a38353b651140b4122709731651be9df53267f428fba6214eb9e43a515d63df0` |
| `vendor_dlkm.img` | `4c50a1c705403a3e6416215f052729d1aed648bc440c4b1b296ef6d65a26c2e0` |

Schema v2 records these outputs and sets
`boot_image_packaging=true`, `packaging_outputs_promoted=false`, and
`flash=false`. Their reproducibility is outside the R4W1 raw-Image verdict
because the eventual live candidate must be packaged separately under an exact
boot-only policy.

## Final G/H Gate

G and H were created independently from the source baseline without `out/`.
The three Samsung archive symlinks that a prior baseline build had rewritten
were restored directly from the pinned base archive in each final tree. Both
schema v2 preflights passed the complete 166,037-member source reconstruction,
stock baseline, Clang identity, four repository pins, four runtime controls,
host-tool overrides, and the 17-tool manifest before either build started.

Both final Full-LTO builds completed without process swaps:

| Run | Elapsed | Peak RSS | Build result SHA256 | Static result SHA256 |
| --- | ---: | ---: | --- | --- |
| G | `37:06.59` | 24,242,528 KiB | `97e694953125439cd69a6d16b49b6493fa2d373ef1b36f6c3a6d9564c249f1a7` | `2d2653f00044da98470e93dc993d6c11be078d1df713d8220e42e85c3a692ce5` |
| H | `35:54.47` | 24,243,240 KiB | `6963f8894de88b1468d5c4f01961152276ad9c7aced49d5b5490f3bc37267bc0` | `5e4b93d427758ba4e178b3d77ee3f3b858caecb0a26f0062d3986b9b526394cb` |

Each build independently passed exact source/patch identity, Full LTO, exact
FYG8 banner, all required output and module gates, provider closure, witness
geometry, and exact restoration of timestamp, KMI-path, VDSO-path, and global
kernel-debug-path controls. Each static audit returned blocker count zero and
`PASS_R4W1_STATIC_COMPATIBILITY`.

The final cross-tree checker returned
`PASS_R4W1_CLEAN_REPRODUCIBILITY`, blocker count zero, and result SHA256
`71ab56b4c56010225145b82899535fbb9680c455e78aec19cebb39f39ad2cbd8`.
Its artifact bindings point to distinct G and H paths for the first four rows
below. Together with the independent G/H build-output records, they prove:

| Artifact | Shared SHA256 |
| --- | --- |
| raw `Image` | `9552653de86dbdc2f1abd919b4d7b0d3f365fc878a56ed5ae09c82d0d81d844c` |
| `.config` | `9c54c862ac5b6a7f1c29a89041eb027458bc0c1189243bce99cd9ed0eba39efc` |
| `vmlinux.symvers` | `fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19` |
| `abi.xml` | `3660c592e1884ab323816c09a3abd197744c8b2f78aed890b02c3e69dbc1c55c` |
| `vmlinux` | `5a76e70205fb453c3381e66dcd0def4b795e0451edb774ccdbc5164f0668aec0` |
| `System.map` | `c91df6227ddc956936686954f0df27a512511e60543718388cb2f65cb4772779` |

Both `vmlinux` files have build-id
`d05ba7ae3b233e5aceceb2d61e7f8bf7d1941600`. Neither raw Image contains
the host build root or its G/H work-tree label. Neither `vmlinux` contains its
G/H source or object-tree path; both contain the same 53 `/kernel-out` stable
aliases and the same fixed toolchain include path. This closes the E/F
top-level build-id discrepancy without claiming cross-host reproducibility.

The raw Image is exactly 41,490,944 bytes, contains the witness marker once,
and preserves 1,536 bytes before the fixed ramdisk start. The exported
symbol/CRC map and `abi.xml` are byte-identical to the pinned baseline. The
host-generated packaging side outputs remain non-promoted and outside this raw
Image reproducibility verdict.

## Source And Tests

Relevant commits:

- `c2d6b9fa`: initial R4W1 witness and host gates;
- `da79ab7b`: reproducible build hardening;
- `0b8a75ac`: artifact/work-tree binding;
- `144be7e0`: sec-log writer timing gate;
- `5fe6add3`, `7b8b4e41`: VDSO path controls;
- `dcbcf091`: global kernel DWARF path control;
- `4121b058`: ABI, host packaging, and effective-tool provenance.
- `95eec5dc`: build-influence audit;
- `93033fcb`: final G preflight record.

The final same-session Claude Opus read-only review returned `GO` for the
same-host raw-Image/KMI/ABI/layout verdict and documentation commit. It
independently checked both build results, both static audits, the cross-tree
result, artifact bindings, path-control restoration, and non-promotion safety
flags. Two low-severity wording findings were corrected here: the four
artifacts directly bound by the repro checker are distinguished from
`vmlinux`/`System.map` build-output evidence, and peak RSS is expressed as
approximately 23.12 GiB rather than treating the raw KiB figure as GiB. The
review explicitly did not extend GO to runtime witness behavior, packaging,
device contact, or flash.

Current focused tests: 48 PASS. `py_compile` and `git diff --check` pass.

## Boundary

No generated kernel, boot image, AP, raw build JSON, or static evidence JSON is
committed. They remain private outputs. This host PASS proves only that this
kernel change is same-host reproducible, KMI/ABI-compatible, layout-compatible,
and ready for a separately designed R4W1-A stock-Android positive-control live
gate. Packaging a live boot candidate, device contact, and flash remain
unauthorized until a fresh SHA-pinned one-shot `AGENTS.md` exception and
attended approval exist.
