# S22+ FYG8 P2.21 artifact closure host pass

Date: 2026-07-22 KST
Tier: H0, host-only build, packaging, and independent static validation
Status: `PASS_P221_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY`
Live authority: none

## Result

P2.21 built the reviewed P2.19 FYG8 kernel with the proven clean Full-LTO
engine, constructed one private boot-only AP without a run/ready manifest, and
independently re-derived the full artifact closure required by P2.20.

The clean build ran for 36 minutes 34 seconds and passed every inherited source,
toolchain, KMI, module, kernel banner, fixed boot-layout, source-restoration,
and output gate. The P2.19 patch SHA remains
`6bf03ca0d3448e0a707b03815e94d8ef5c059e9aaa14f3612a0bb953f3758c44`.

## Build Artifacts

The immutable host contract pins these private outputs:

| Artifact | Size | SHA256 |
| --- | ---: | --- |
| `Image` | 41,490,944 | `3afa1c8121c6040e09329abae4d0a8a61ff0f9ee7fe37ed311e1b2e56ab24ce5` |
| `vmlinux` | 476,932,816 | `83e5cdc23143f69f2be22038f39cbb5c427999fe3ffc63a32319ee0aab77e06e` |
| compiled `.config` | 185,347 | `cf6f6c91bc572daa7d6d44cf6ac7a693698443ed32dc1a0748b769bf99329684` |
| build result | 679,932 | `5d9bca09726c1dca27ce6b74e1da7401575cd79ce57249bc6abaa147fc0d6c19` |

The compiled config contains exactly one
`CONFIG_S22PLUS_FYG8_PID1_SAME_RING_DISCRIMINATOR=y`. Image and vmlinux each
contain exactly one ENTRY, one USERSPACE, and one UNSAT record, two long-family
records, one UNSAT-family record, and zero retired E0 records. The Image keeps
the exact 41,490,944-byte kernel slot and fixed ramdisk start.

The build restored all three patched source files to their exact base hashes.
It also restored the source archive's absolute audio-header symlinks after the
vendor build.

## Candidate Artifacts

Construction pins the previously qualified E0 boot as a ramdisk carrier, then
replaces only `[4096, 41495040)` with the new exact Image. Header, alignment,
ramdisk, and every byte outside that fixed kernel interval remain unchanged.

Private candidate receipts are:

| Artifact | SHA256 |
| --- | --- |
| `boot.img` | `d2d4b679bea5847c8ed9570870c037c6adad880eb429479c51cec5beddfcc9be` |
| `boot.img.lz4` | `c4c1a60aade88faf87f1232c7b7ad0938d35cc3a509b122b0313eb163f3bc608` |
| `odin4/AP.tar.md5` | `73e550d53bb0c2f4a8d69fd85829a1fe65e8e1af39069e9e749fe8e81956342e` |

The output directory contains only `boot.img`, `boot.img.lz4`, one
`odin4/AP.tar.md5`, and an H0 artifact result. It contains no `manifest.json`,
`run-manifest.json`, Process v2 ready manifest, approval, or live binding.

## Independent Closure

The independent checker did not reuse the builder's fixed-interval
reconstruction. It separately:

1. verified the pinned Image, vmlinux, compiled config, and build result;
2. reconstructed the candidate boot from the exact carrier and Image;
3. parsed the AP MD5 trailer and canonical USTAR inventory as exactly one direct
   regular `boot.img.lz4` member;
4. decompressed that member with the pinned LZ4 tool and recovered the exact
   submitted boot image;
5. unpacked boot with the pinned `magiskboot` tool and recovered a kernel
   byte-identical to the checked Image;
6. recovered the exact static `/init`, size 66,056 and SHA256
   `c3fd6cc88d8de494421ff2bf0f082d278745fdf9c2a74a2b5edba9fb8ca93627`;
7. bound the exact child from the pinned two-build runtime receipt; and
8. proved the pinned init loads only `smem.ko`, `minidump.ko`, `qcom-scm.ko`,
   `qcom_wdt_core.ko`, and `gh_virt_wdt.ko`.

The exact runtime source and extracted rootfs contain no `sec_log_buf.ko` load,
direct `0x800200000` writer, `/dev/mem`, or block-write path. The static result
verdict is `PASS_P221_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY`.

## Fail-Closed Observations

- The first build-host preflight refused a source copy because three
  archive-owned audio-header symlinks still pointed at an earlier temporary
  vendor-build path. Only the P2.21 copy was restored to the archive-recorded
  targets; the second preflight passed.
- The first real artifact-contract run rejected a misspelled config-symbol
  constant. The contract now uses the exact P2.19 symbol from the compiled
  config.
- The first independent candidate check rejected a manually transcribed child
  digest. The checker now derives the child receipt from the already pinned,
  two-build runtime receipt rather than duplicating that constant.

No failed check caused a build, package, transfer, or device action to be
repeated.

## Boundary

This unit contacted no device, invoked no Odin transport, performed no transfer
or flash, created no ready manifest, and grants no D0, D1, F1, or live
authority. Cache-to-DRAM retention remains a later live acceptance property.

The next bounded unit is P2.22: fresh connected read-only D0 qualification and
candidate-specific ready-manifest preparation. It must not transfer the
candidate or imply F1 approval.
