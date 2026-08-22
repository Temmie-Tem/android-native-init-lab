# A90 exact-toolchain H33 identity-only materialization — H0

Date: 2026-08-22
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only materialization
Device contact: none
Authority: no D0, D1, F1, approval, transfer, reboot, or live authority

## Result

H33 is a fresh candidate identity built from the same accepted Snapdragon
LLVM 10.0.7 stock-rebuild input and functional manifest leaves used by H32.
It is not H32 replay: the version, build identity, cycle, decision, random
seed, enable/latch paths, and init banner are H33-specific. `candidate_authority = false`
remains explicit. H32 is consumed and supplies no boot result.

The H33 preparation does not create an approval, qualification verdict, D0
binding, F1 intent, transfer, reboot, or device claim. Independent review is
required before any H33 qualification can be considered.

## Materialized result

The flat builder ran once on the host with the H33 manifest and the already
bound observer-public-key input. Output is isolated at
`workspace/private/outputs/a90-h33-stock-rebuild-1007-cfp-ab-20260822-01/`.

| Item | Size | SHA-256 |
|---|---:|---|
| H33 flat manifest | — | `10c26569cfac1202b364e7693665a17e32f3367b26ea4dd805934b8cea22aa58` |
| H33 effective manifest | — | `591967b80e3b67ce01e1592819912e164cba3e58f6bbbcc10ca35e5a900a45a2` |
| H33 A/boot.img | 58,372,096 | `bdbcfc5fb82150c2d508df1e4d7ae7b71f0659b7d6b02ddab506f263f6063e12` |
| H33 B/boot.img | 58,372,096 | `bdbcfc5fb82150c2d508df1e4d7ae7b71f0659b7d6b02ddab506f263f6063e12` |
| A/B receipt | 5,426 | `edb7f6fcf2e8431995e459a68cf2f5c8274794fee40da114dce780ca11b9fd0e` |
| H33 init | 1,723,376 | `ad8814f56f4d816f6645b048030a1f844eac9deebaea73b28e90a9593c691ae1` |
| H33 ramdisk | 8,537,600 | `a3ef569715e71390f407977833d3ff6ba56ca56ff81a66dc3fdd43506bfd8f5a` |
| exact kernel blob | 49,827,613 | `59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac` |
| kernel Image | 48,830,480 | `6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557` |

A and B are byte-identical. The kernel blob and embedded Image are byte
identical to H32's recorded kernel and Image. The complete boot artifact is
deliberately different from H32 (`e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d`),
because the H33 init identity is new. The ramdisk contains the H33 banner
`A90 Linux init 0.11.200 (phase3-minimal-h33-stock-rebuild-1007-cfp)` and not
the H32 banner.

## Bound inputs and limits

- Base boot input is the same host-staged accepted stock-rebuild input as H32;
  its SHA-256 is pinned by the builder receipt.
- The exact kernel source payload is functionally reused, not treated as proof
  of H33 boot, vendor-module compatibility, stock byte equivalence, or full
  reproducibility.
- Current owner closure is `48cb09e35b25f02e15fde091c93f2755b366fcb561210df49ffbafea3d333854`.
  The current candidate-return continuation capability is
  `a62318c74c334509560f7c84fead011eb0a0c7fa6d8a80a45b4d72539a97a4df` with
  current review digest `6bf984a2c5ff7ce3b7487b1af63073a88664c130f0137a9e2ab40104db47aac8`;
  these are capability inputs only and grant no H33 authority.
- H32, H31, H30, and H29 remain consumed. Their observations cannot be
  relabeled as H33 evidence, and no candidate or rollback write is authorized
  here.

The next bounded step is independent review of the H33 public qualification
input and exact owner/manifest closure. Until that review exists, H33 remains
H0 preparation only.
