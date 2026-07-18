# S22+ FYG8 R4W1-B Reusable Candidate Pipeline Host PASS

Date: 2026-07-19 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Scope: host-only implementation and qualification of the minimal reusable
fixed-slice candidate pipeline. No device was contacted or enumerated. No ADB,
Download transition, real Odin transfer, flash, consumed state, timeline, live
helper, or policy activation occurred.

## Result

The implementation completed the full sequence in
`S22PLUS_FYG8_R4W1B_MINIMAL_REUSABLE_CANDIDATE_PIPELINE_DESIGN_2026-07-19.md`:

1. builder-only primitives and tests;
2. checker-only independent parsers and tests;
3. frozen R4W1-A historical fixture qualification;
4. exact R4W1-B builder and tests;
5. three fresh builder processes;
6. independent R4W1-B checker and mutation tests;
7. complete host-only qualification.

Durable verdict:

`PASS_R4W1B_CANDIDATE_THREE_REPRO_STATIC_CONTRACT`

`blockers: []`

Static result:

```text
size    30004
sha256  969b4a5d94660fb07abba95fe2386cb9327c2a0e97167e153a895619c4385d47
```

## Implementation

Builder-side mechanics are isolated in `s22plus_boot_slice.py`. They contain
no target pins or geometry and provide stable direct-file reads, fixed interval
replacement, outside-interval checking, ARM64 header parsing, deterministic
single-member AP generation, marker-family classification, and the fixed
nonexistent-device Odin gate.

Checker-side mechanics are isolated in `s22plus_boot_verify.py`. It does not
import builder code. It independently parses boot v4, vendor_boot v4, AVB,
USTAR/MD5 APs, LZ4 frames, newc CPIO archives, and the complete executable
footprint of the selected AArch64 `/init`.

The target programs are:

- `build_s22plus_fyg8_r4w1b_candidate.py`;
- `s22plus_fyg8_r4w1b_candidate_static_checker.py`;
- `s22plus_fyg8_r4w1b_historical_fixture_check.py`.

The checker imports neither the builder nor builder-side primitives. Its
load-bearing construction is independently written as:

```text
carrier[:4096] + image + carrier[41495040:]
```

## Exact Inputs

```text
M4T2 carrier       100663296  8103bce76fb3e41d71b64735a64d2f2f29431a44ea1c9a85dc0bc151d71afd15
R4W1-B Image        41490944  350bc71815a7dbf22caf5d42434e4f99ace846329fd11e599b3be2d9c5e080d3
kernel repro result    314695  1b1124c828243772cb48cf8aa7f6667e88cd9ac5443164e2042243510d833eb1
stock vendor_boot   100663296  096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
lz4                    218696  91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8
Odin4                  3746744  6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b
avbtool                14060849  063d7c7a19744ceeb72553c95962ac98fff977fc27f5f95e6063c2f15f8d3e88
```

The Image was reopened on both clean build trees before transfer. Both remote
paths still produced the exact `350bc718...80d3` SHA. The local copy was then
rechecked for exact size and SHA before candidate work.

## Three Reproductions

Each builder invocation started as a fresh process and wrote a previously
absent output directory. Reproductions A, B, and C have identical identities:

```text
boot.img       100663296  69690e6832bab2a422979054b51ad279222c14cbc369517433b55a785ed3d44d
boot.img.lz4    27055052  be2265ae72c584553945a82cdabc1ce36cc59cf6ee065c9675b97df9fc209c9a
AP.tar.md5      27064361  ae26340d69f7208ae3a8c0d135e3f65317b4d16b539d4e19c1613b7f15f0f2c5
manifest.json       4150  46c29171bfe640fb81b4dc36b8f342364c73055274145f413f29e0c8e36c65b0
```

The manifests contain no timestamp, hostname, absolute path, inode, or output
directory. They are byte-identical receipts and are not checker trust roots.

## Independent Proofs

The checker established:

- exact boot v4 header preservation and unchanged kernel size;
- exact qualified Image bytes and ARM64 header in the final kernel interval;
- exactly one exact R4W1-B marker, with no foreign, partial, duplicate, or
  historical-family record;
- exact preservation of `[41495040,41496576)` and every opaque post-kernel
  carrier byte;
- exact single-member `boot.img.lz4` AP, strict USTAR metadata, exact MD5
  trailer, strict single LZ4 frame, and full raw round-trip;
- three distinct directories and no hardlinked raw, LZ4, AP, or manifest
  artifacts;
- exact M4T2 AVB footer/vbmeta preservation;
- sealed-memfd `avbtool` outcome for carrier and candidate: vbmeta signature
  valid, payload hash mismatch, nonzero return, as required for intentional
  stale AVB;
- stock vendor_boot v4 SHA and its one table fragment;
- final rootfs composition `generic -> vendor[0]/<unnamed>` with 473 unique
  entries and no duplicate, override, symlink, or hardlink alias;
- no `rdinit=` in boot cmdline, vendor cmdline, or vendor bootconfig;
- exactly one effective regular `/init` in the generic ramdisk, UID/GID `0/0`,
  mode `0750`, size `544`, SHA256
  `b8371e3ac671ff71e9be752b8ff1087a4f20811c871a43ca8e698eee47783d12`;
- exact `/init` executable footprint of two AArch64 instructions:
  `0xd503205f` (`wfe`) and `0x17ffffff` (`b` back to entry), with no PT_INTERP
  and no syscall instruction.

## Historical Fixture

The new builder mechanics independently reconstructed the frozen R4W1-A raw
boot and deterministic AP exactly. The result is:

```text
verdict PASS_R4W1B_BUILD_PRIMITIVES_R4W1A_FIXTURE
size    2066
sha256  5a57c73f97c86d3c54117cf40ff1ef320ddc20057622352c207cafab08de0a66
```

No historical source, manifest, result, or report was edited.

## Validation

```text
focused new tests                         34 passed
focused + frozen R3/R4W1-A regressions   72 passed
py_compile                               PASS
git diff --check                         PASS
ruff                                     unavailable on this host
```

## Boundary And Next Step

This PASS qualifies host construction and static evidence only. It does not
prove live boot, retained-marker recovery, rollback, or device behavior and it
does not activate any exception in `AGENTS.md`.

The next bounded unit is an adversarial review of the exact implementation,
tests, private artifacts, and this result. Any future device action requires a
separate live design, checked helper, pinned artifacts, binding policy, fresh
attended approval, and rollback gate.
