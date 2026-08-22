# A90 exact-toolchain H34 identity-only materialization — H0

Date: 2026-08-22
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only materialization
Device contact: none
Authority: no D0, D1, F1, approval, transfer, reboot, or live authority

## Result

H34 is a fresh candidate identity built from the same accepted Snapdragon
LLVM 10.0.7 stock-rebuild input, observer key, and functional manifest leaves
used by H33. It is not H33 replay: the version, build identity, cycle, decision,
random seed, enable/latch paths, and init banner are H34-specific.
`candidate_authority = false` remains explicit. H29–H33 are consumed and
supply no H34 boot result.

The H34 preparation does not create an approval, qualification verdict, D0
binding, F1 intent, transfer, reboot, or device claim. No H34 independent
review exists yet; this report stops at H0 materialization.

## Materialized result

The flat builder ran once on the host with the H34 manifest and the accepted
base/key inputs. Output is isolated at
`workspace/private/outputs/a90-h34-stock-rebuild-1007-cfp-ab-20260822-01/`.

| Item | Size | SHA-256 |
|---|---:|---|
| H34 flat manifest | — | `d2f27becfe42491519dd82defafaa82bb974e125dfc937b38f44b62370c5014d` |
| H34 effective manifest | — | `77de213ddbb02a2e4c5abec91e1f0b454717c1c62dd0cbf2504f4c225336cd19` |
| H34 A/boot.img | 58,372,096 | `233bfdcac20d5fdc1184a907e8e8b5cd4d2c1286dc08a8f6028cfcf5c90ad4ee` |
| H34 B/boot.img | 58,372,096 | `233bfdcac20d5fdc1184a907e8e8b5cd4d2c1286dc08a8f6028cfcf5c90ad4ee` |
| A/B receipt | 5,426 | `606ff98cd06a4caa8f1f5e35bcc18dea85352ee0e458a0bf49b074fc2329eb3f` |
| H34 init | 1,723,376 | `8db6761a87106024245ab3ab63fc2cd93f315b08525a92f247141984c92acfe0` |
| H34 ramdisk | 8,537,600 | `d0958f058df2369bd17fd163690833301389ad41564d47ee17e8357bcedb5be9` |
| exact kernel blob | 49,827,613 | `59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac` |
| kernel Image | 48,830,480 | `6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557` |

A and B are byte-identical. The kernel blob and embedded Image are byte
identical to H33. The complete H34 boot artifact is intentionally different
from H33 `bdbcfc5fb82150c2d508df1e4d7ae7b71f0659b7d6b02ddab506f263f6063e12`,
because the H34 init identity is new. The ramdisk contains the H34 banner
`A90 Linux init 0.11.201 (phase3-minimal-h34-stock-rebuild-1007-cfp)` and not
the H33 banner.

## Bound inputs and limits

- Base boot and observer-key inputs are the same host-staged inputs used by
  H33; the builder receipt pins their hashes.
- Functional/kernel equivalence is host evidence only. H34 boot, Android/vendor
  external-module compatibility, stock byte equivalence, and full
  reproducibility remain unproved.
- Current owner closure is
  `1c31fb97e8f181e63bd71949b020f647aa8dab45c63d13bd089f6be2659da8a8`.
- Current candidate-return continuation closure is
  `d053e137ca6d984709e53a1200d1e980f6d766ab4dd30cbb012cef2ddd3ee9e1`, with
  current review SHA
  `22c0e6a60eb94dd5407d995c8e4b7e283bb149057e0ecbf8164dae5e613b49e9`.
- Current postrollback recovery review SHA is
  `429c84e57b873619fd840df7afa009d52a99560de6a4c461cf84da3c73aa5429`.
  These are capability inputs only and grant no H34 authority.

The next bounded step is independent review of the H34 public qualification
input and exact owner/manifest closure. Until that review exists, H34 remains
H0 preparation only.
