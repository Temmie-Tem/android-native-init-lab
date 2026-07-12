# S22+ FYG8 Kernel Rebuild R1/R2 Host Gates

Date: 2026-07-11 KST
Target: `SM-S906N/g0q/S906NKSS7FYG8`
Scope: host-only source provenance, complete module-corpus, and static ABI gates

## Verdict

**R1/R2 host infrastructure is ready. R1 and R2 themselves remain pending the
unchanged Full-LTO run on the controlled 32 GiB host.**

No boot image was packaged, no device was contacted, and no flash or partition
write occurred.

## R1 Preflight v2

`s22plus_fyg8_kernel_build.py` now performs the source audit inside each
preflight instead of trusting a prior manifest. The live host run rehashed the
pinned FYD9 base plus FYG8 delta and matched all 166,037 resident members with
zero missing or mismatched files.

The wrapper now:

- starts from a minimal host environment allowlist and a pinned PATH;
- rejects ambient compiler flags and shell hooks;
- verifies all four exact tool repositories and Clang `r416183b` identity;
- requires Image, Image.lz4, vmlinux, System.map, vmlinux.symvers,
  modules.builtin, modules.builtin.modinfo, and `.config`;
- fails a zero-return build when no generated `.ko` exists;
- hashes every generated module and symvers file into the result.

All source, toolchain, isolation, disk, and host-tool gates pass locally. The
only rejection is physical RAM: 15.2 GiB observed versus the 30 GiB Full-LTO
floor. This is the intended fail-closed result.

## Exact Super Layout

The stock AP's `super.img.lz4` expands to an Android sparse image of
10,352,130,812 bytes, SHA256
`f418abff8cf0612d7c145d6f6de0ac6a13bbdd8b5a6458b5ae8c18f2bf8243c8`.
The raw logical image is 12,475,957,248 bytes, SHA256
`63061c093dce2e1f0a3df41bf0a960b72f221ecca8277c9f2fcc20a3e8e8f4ae`.

Primary geometry, metadata-header, and table SHA256 checksums all pass. The
partition set is exactly:

```text
system odm product system_ext vendor vendor_dlkm
```

There is no `system_dlkm` or `odm_dlkm` logical partition. Recursive read-only
F2FS walks found zero `.ko` files in `system`, `vendor`, and `odm`.

The parser follows the official Android `liblp` metadata format and the
official `lpunpack` extent model:

- https://android.googlesource.com/platform/system/core/+/master/fs_mgr/liblp/include/liblp/metadata_format.h
- https://android.googlesource.com/platform/system/extras/+/master/partition_tools/lpunpack.cc

## Complete Module Corpus

The exact `vendor_dlkm` partition is 57,610,240 bytes, SHA256
`e5386d68ccf9ad1a12cfa4cf447e704bddcef94b0442e61765f3dba580186b26`.
Its F2FS `/lib/modules` contains 356 modules and five depmod metadata files.

The host reader reconstructs compressed F2FS clusters directly. It parses the
inode/direct-node address maps, validates the LZ4 compressed length, expands
each cluster with `LZ4_decompress_safe`, truncates to the inode size, then runs
modinfo and modversion inspection on the recovered ELF.

Directory/inode metadata came from `dump.f2fs 1.16.0`; the locally extracted
multicall binary SHA256 is
`66db38ca0ea8239cab0c335e142ee34751824352eaa494b3654fa7d663b86669`.
Compressed file content is reconstructed by the project reader rather than
trusted to `dump.f2fs`, because that tool's inode dump does not expand these
compressed clusters.

Corpus result:

| Measure | Count |
|---|---:|
| Vendor-ramdisk modules | 441 |
| vendor_dlkm modules | 356 |
| Names present in both | 306 |
| Overlap byte-identical | 306 |
| vendor_dlkm-only | 50 |
| Vendor-ramdisk-only | 135 |
| Complete unique union | 491 |

There are zero overlapping content mismatches. The complete consumer contract
contains 25,864 module/symbol CRC rows over 4,619 unique symbols.

## ThinLTO Diagnostic

The old diagnostic is deliberately non-R1: its release is only
`5.10.226-android12-9`, it uses ThinLTO, and vendor module modpost did not
finish. The new R2 auditor nevertheless gives useful bounded evidence:

| Measure | Result |
|---|---:|
| Consumer CRC rows | 25,864 |
| Rows satisfied by GKI symvers | 22,600 |
| Missing module-provider rows | 3,264 |
| Unique missing symbols | 1,743 |
| CRC mismatches | 0 |
| Generated Image fits stock boot layout | yes |

The missing rows do not prove a KMI break. They are unresolved until the Full
LTO vendor build returns its provider symvers. The zero mismatch among all
present providers is positive diagnostic evidence only.

## Remaining Gate

1. Transfer the pinned 20-file/four-repository kit to the Debian 13 FX-8300
   32 GiB host.
2. Require exact R1 preflight PASS and run unchanged Full LTO under `tmux`.
3. Return the R1 result, all owned outputs, generated modules, and every symvers
   file.
4. Run the prepared R2 audit. Any release, config, CRC, output, or corpus
   identity mismatch remains FAIL.

R3 packaging or device work remains unauthorized until both gates pass and a
fresh boot-only policy exception is added.
