# A90 exact-toolchain H32 identity-only materialization — H0

Date: 2026-08-22
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only materialization
Device contact: none
Authority: no D0, D1, F1, token, approval, or live authority

## Result

H32 clones every H31 functional manifest leaf. Only these identity values
change:

- version `0.11.199`;
- build `phase3-minimal-h32-stock-rebuild-1007-cfp`;
- cycle `H0-PHASE3H32`;
- decision `phase3-minimal-h32-exact-h31-functional-byte-reuse`;
- random seed `a90-phase3-minimal-h32-stock-rebuild-1007-cfp`;
- `/cache/a90-auto-handoff-phase3-minimal-h32.enable` and `.done`;
- the matching H32 version banner.

`candidate_authority = false` remains explicit. H31 is not replayed or
reclassified. This public identity grants no qualification, approval, transfer,
reboot, or device authority.

## Materialized result

The operator ran the flat builder once with the same accepted stock-rebuild
base and observer public key used for H31. Output is isolated at
`workspace/private/outputs/a90-h32-stock-rebuild-1007-cfp-ab-20260822-01/`.

| Item | Size | SHA-256 |
|---|---:|---|
| H32 manifest | — | `6678acc7e2e9337819f5f176448f549f1501f12105b304f9ac6c93b86750d3d3` |
| H32 effective manifest | — | `543d97a79db6ab0136ba6ef823ecc49b8f3558e98ace6ba37043c989ace74292` |
| H32 A/boot.img | 58,372,096 | `e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d` |
| H32 B/boot.img | 58,372,096 | `e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d` |
| A/B receipt | 5,426 | `5c075189edb5b2c48383aeb68a9f071c85cf031b6eedb5f9df08095825ff1dbc` |
| exact kernel blob | 49,827,613 | `59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac` |
| kernel Image | 48,830,480 | `6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557` |
| H32 init | 1,723,376 | `3769b4f571d60d55ed246b99a688d9ef5f38e0baa991b1c71f957228c8f5c8ae` |
| helper | 1,649,904 | `fcb005b0454aceb08aa6f8f81d83aa303e37199a56e018eb2501e4225f08e00e` |
| H32 ramdisk | 8,537,600 | `ca4ea8651d7c4ed0d9a4124c5fb5bae81d839e06b446adf5652cd014b1aaf113` |

A and B are byte-identical. The exact kernel and Image match H31; the H32
banner is present and the H31 banner is absent. Candidate authority remains
false. The private branch was verified with `A90_H32_VERIFY_PRIVATE=1`.

## Public validation

`tests/test_a90_stock_rebuild_1007_h32.py` proves H32/H31 functional-leaf
equality and exact H32 identity/state changes using public files only. Its
private artifact branch is disabled by default and performs no private lookup
unless explicitly enabled.
