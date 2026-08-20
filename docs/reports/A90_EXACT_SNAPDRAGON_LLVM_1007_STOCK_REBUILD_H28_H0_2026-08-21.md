# A90 exact Snapdragon LLVM 10.0.7 stock-configuration rebuild and H28 materialization

Date: 2026-08-21
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host build and private candidate materialization
Device contact or effect: none
Disposition: the exact-toolchain rebuild and deterministic H28 boot artifact are
materialized; whether A90 boots this kernel remains **unproved**

## Result

The A908N Android 12 OSRC kernel builds without disabling Samsung RKP CFP when
compiled with the published Snapdragon LLVM 10.0.7 toolchain named by the
vendor Makefile. The qualifying build preserves the source defconfig's
`CONFIG_UH_RKP=y`, `CONFIG_RKP_CFP=y`, `CONFIG_RKP_CFP_JOPP=y`, and
`CONFIG_RKP_CFP_ROPP=y`. The post-link CFP instrumenter and FIPS update both
complete.

The resulting raw arm64 `Image` is 48,830,480 bytes, the same size as the
stock Image. It is not byte-identical to stock and is not called stock. The
bounded claim is:

> this is a source/configuration-zero A908N rebuild made with the exact
> published vendor compiler generation, packaged into a fresh H28 identity;
> device acceptance is still a separate attended boot experiment.

No D0, D1, F1, candidate execution, approval, transfer, reboot, or flash
authority follows from this report.

## Correction to the 2026-08-16 prior

`A90_SELF_BUILT_KERNEL_H0_2026-08-16.md` stated that the required CFP compiler
was not published and recorded disabling CFP as an authorized deviation. That
conclusion is superseded.

The public Qualcomm vendor dump at
`comprehensive9/vendor_qcom_proprietary`, branch `11se`, commit
`36fc163a534963a5b3af52186af5efcc63401ad2`, contains
`llvm-arm-toolchain-ship/10.0/`. Its `RELEASE_NOTES` identifies the package as
Snapdragon LLVM ARM C/C++ Toolchain 10.0.7 and enumerates the changes from
10.0.6. The compiler reports both:

```
clang version 10.0.7 for Android NDK
Snapdragon LLVM ARM Compiler 10.0.7 for Android NDK
```

It accepts all three flags that the prior AOSP compiler rejected or silently
dropped:

```
-mllvm -disable-struct-const-merge
-mllvm -cfp-jopp
-mllvm -cfp-ropp
```

The exact `clang` is 96,189,952 bytes, SHA-256
`453971166fa1b628df189e602f355cb2c58c12cd289515400ee6260c9a83459d`.
The 10.0.6 mirror was also tested and accepts the flags, but it is not the
selected compiler because the stock banner names 10.0.7.

H27 remains a real failed candidate and must not be replayed. This correction
does not relabel its boot-loop cause: that cause remains unproved. It only
removes the earlier claim that CFP had to be disabled to build.

## Frozen inputs

| Input | Exact identity |
|---|---|
| OSRC outer ZIP | `d0a6c9f29387a6ba9d5fe0ad8c1a1e79576f4d0c0bc463394f1cd70389897a3b` |
| `Kernel.tar.gz` | `403fdc49f086d238c01a796c390083c3c47c1754c218e228f29b55cc7c35d554` |
| board defconfig | `r3q_kor_single_defconfig` |
| Snapdragon LLVM repository | `36fc163a534963a5b3af52186af5efcc63401ad2` |
| Snapdragon LLVM `clang` | 96,189,952 / `453971166fa1b628df189e602f355cb2c58c12cd289515400ee6260c9a83459d` |
| GNU 4.9/gold repository | `606f80986096476912e04e5c2913685a8f2c3b65` |
| stock V2321 boot | 60,882,944 / `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb` |
| prior flat-builder base | 66,375,680 / `2d0be40158d56b6b053bc1aff6c6e149beb904da43a303b812e8ca6c4d583a9e` |

The build used the stock metadata:

```
KBUILD_BUILD_USER=dpi
KBUILD_BUILD_HOST=SWDK6110
KBUILD_BUILD_VERSION=2
KBUILD_BUILD_TIMESTAMP=Thu Jan 12 18:53:40 KST 2023
LOCALVERSION=-25818860-abA908NKSU5EWA3
TIMESTAMP=2023-01-12T09:49:35Z
```

The resulting banner is exactly:

```
Linux version 4.14.190-25818860-abA908NKSU5EWA3 (dpi@SWDK6110) (clang version 10.0.7 for Android NDK, GNU ld (binutils-2.27-bd24d23f) 2.27.0.20170315) #2 SMP PREEMPT Thu Jan 12 18:53:40 KST 2023
```

## Host compatibility preparation

The released tree assumes Samsung's larger internal workspace. The tracked
`a90_stock_rebuild_1007_prepare.py` performs only the following bounded host
compatibility work:

- normalize CRLF to LF in exactly three Makefiles;
- materialize 26 already-present ION/audio byte mappings, of which 22 were
  missing regular destinations and four were already exact in-root symlinks;
- preserve 63 existing audio includes rather than overwrite them; and
- create the two expected `out/kernel/msm-4.14` and `msm-4.19` audio links.

Its canonical private receipt reports `semanticSourceChanges: 0`, SHA-256
`988acf14c0ec8dadad12e71a5b6956254394bcd397bdd24d9d6362a58e5075c1`.
No C, header, Kconfig, defconfig, compiler option, or RKP/CFP script was patched.

The generated `.config` is 188,380 bytes, SHA-256
`e4b7fa2f4fd6055eecfc7fd7b7546ab3e77ffdaf8ee77da27c9f341646f77f8b`.
Relative to the defconfig, Kconfig only makes twenty unrelated Samsung project
choices explicit as `n`; no enabled symbol or configured value changes.

## Qualifying kernel build

The qualifying clean build C produced:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `Image` | 48,830,480 | `6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557` |
| `Image-dtb` before stock DTB append | 48,830,500 | `ad65d24279b0f64bed493abf142b34cd38d7ffe26d71c0743c69a03c4b8e4dfc` |
| `System.map` | 6,363,530 | `573d61f1d6fcefbe3f9b0b1ccb88dad92eeddbb449ad45baa26c22233c25bf74` |
| build X.509 | 1,324 | `c773e5d46d151f8e10e966c1fbeba21dd49213dc80d057ecc9a7e200a8bc26db` |

`System.map` contains 31 matches for `rkp_cfp`, `jopp_springboard`, or
`ropp_`, and three for `rkp_init` or `uh_call`. The build log records RKP CFP
instrumentation and the FIPS HMAC update. The sole known linker warning remains
the vendor-tree `gsi_write_channel_scratch` modversion warning.

Two earlier clean discovery builds also completed, but generated different
module-signing certificates and WLAN build timestamps. A later exact-byte
reproduction attempt was invalidated when an interrupted remote make process
was found still alive beside its successor. Both process groups were stopped
and the mixed output was rejected. Therefore full kernel bit reproducibility
is **unproved**; build C is the sole selected, hash-pinned kernel artifact.
This does not weaken candidate integrity because the exact bytes sent by a
future F1 are independently fixed below.

## Module-signing boundary

The stock Image embeds a 1,357-byte build-time certificate, SHA-256
`8fe91927138761f729152cf6271c42523e7c098b616b3c098d0a804e5c7462e3`.
Its private key is unavailable, so a source rebuild necessarily carries a new
build certificate. This means stock external-module trust equivalence is
unproved.

That limitation does not silently become a proof obligation for the narrow
Native boot check: the V2321 ramdisk contains no `.ko`, and the selected A90
native-init source has no module-loading action. It remains a named limitation
for any later Android/vendor-module claim.

## Base and H28 packaging

The rebuilt kernel blob is the stock 20-byte `UNCOMPRESSED_IMG` header, the
selected 48,830,480-byte build C Image, and the exact stock 997,113-byte DTB
tail. It is 49,827,613 bytes, SHA-256
`59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac`.

Repacking that blob with the prior flat-builder base ramdisk produced:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| exact-toolchain base boot | 66,379,776 | `5cf27a56b7887b3f766af3caa7c1441cac51d153faf4f64a771902ad7f0118f6` |
| preserved base ramdisk | 16,545,280 | `245c135c34d66b067e17f459fc0ee17f3f0d03be8024289df038a590f18d6eba` |

Re-unpacking proves the kernel and ramdisk hashes above, while all mkbootimg
semantic arguments are equal to the prior base. The file is a base input, not
a candidate and not live authority.

The fresh manifest is
`a90_flat_builder/versions/phase3-minimal-h28/manifest.toml`:

- version `0.11.195`;
- build `phase3-minimal-h28-stock-rebuild-1007-cfp`;
- fresh enable `/cache/a90-auto-handoff-phase3-minimal-h28.enable`;
- fresh latch `/cache/a90-auto-handoff-phase3-minimal-h28.done`;
- manifest SHA-256
  `f8a91278e0a895a6d8d9224e6cf86e0ca97e6115879ce6e556f30ce3122a030e`;
- `candidate_authority = false`.

Independent A/B flat-builder materialization is byte-identical:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| H28 A `boot.img` | 58,372,096 | `aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b` |
| H28 B `boot.img` | 58,372,096 | `aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b` |
| A/B receipt | 5,426 | `2b37e460e9dde802e3d2a6fb46fbd5a72782c5a46b5d21bd3baac660506e029c` |

Re-unpacking H28 proves that its internal kernel is exactly
`59f79b8f...` and that the ramdisk reports the fresh H28 version/build. No H27
enable/latch path is reused.

## What remains before one boot proof

The H27 incident already consumed its candidate attempt and left two explicit
preconditions for any new A90 F1:

1. publish a reviewed terminal-only recovery receipt binding the exact healthy
   V2321 return and release only the retained active-run guard;
2. repair/review the owner so an already-present bound recovery ADB endpoint
   can continue the same untransferred rollback attempt without an
   out-of-owner deviation;
3. independently review the H28 execution-critical closure and the narrowed
   hazard `A90_SELF_BUILT_KERNEL_BOOT_ACCEPTANCE_WITH_NEW_BUILD_CERT`;
4. perform fresh connected D0, prove exact V2321 health and absent H28 state
   paths, then obtain one fresh attended exact F1 approval.

The intended live question is only whether this exact rebuilt kernel reaches
fresh H28 Native health. PASS requires the candidate version/build, exact
`/proc/version`, self-test health, no boot loop, retained physical recovery,
and a terminal structured result. Failure or ambiguity never retries H28; it
uses the one exact V2321 rollback and closes only after V2321 health.

## Boundary

The kernel build ran on the operator-owned LAN build host. Public network use
was limited to the Qualcomm vendor dump and public AOSP toolchain repositories.
Private A90 source, boot, key, build, log, and candidate bytes remain under
`workspace/private/` and are excluded from commit. Device, `/dev`, USB, ADB,
serial, A90 network, S22+, and S20+ contacts are zero. No live authority is
granted.
