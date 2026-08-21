# A90 exact-toolchain H31 identity-only materialization — H0

Date: 2026-08-22
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only materialization
Device contact: none
Authority: no D0, D1, F1, token, approval, or live authority

## Result

H31 is the smallest public successor identity of H30. The H30 functional
manifest leaves are unchanged; only these identity values differ:

- version `0.11.198`;
- build `phase3-minimal-h31-stock-rebuild-1007-cfp`;
- cycle `H0-PHASE3H31`;
- random seed `a90-phase3-minimal-h31-stock-rebuild-1007-cfp`;
- `/cache/a90-auto-handoff-phase3-minimal-h31.enable` and `.done`.

`candidate_authority = false` remains explicit. H30 is not replayed, and this
public preparation grants no qualification, approval, transfer, reboot, or
device authority.

## Materialized result

The operator then ran the flat builder once with the same accepted stock-rebuild
base and observer public key used for H30. The output is isolated at
`workspace/private/outputs/a90-h31-stock-rebuild-1007-cfp-ab-20260822-01/`.

| Item | Size | SHA-256 |
|---|---:|---|
| H31 manifest | — | `e8010aa8d369436db44027894d3de3eec40db38f9990cf790eeb1376690cb3ab` |
| H31 effective manifest | — | `0edad3e9c6a987a8564c241c97d08d370f32bf174797840abe2413e8774e34c9` |
| H31 A/boot.img | 58,372,096 | `5ad0fe043e39482163d10b1870f79c85780c12642bc04d9ee65d3eee8dd323f9` |
| H31 B/boot.img | 58,372,096 | `5ad0fe043e39482163d10b1870f79c85780c12642bc04d9ee65d3eee8dd323f9` |
| A/B receipt | 5,426 | `559e8f655f50e6d9b126dfd2beed6e9d6713ac4ca8ed743b5371d5e4f2fb073a` |
| exact kernel blob | 49,827,613 | `59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac` |
| kernel Image | 48,830,480 | `6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557` |
| H31 init | 1,723,376 | `69958aa04754c97d21b518ad2ec5818eacd3c53b709e8af8fa7fb7d94b4e0902` |
| helper | 1,649,904 | `fcb005b0454aceb08aa6f8f81d83aa303e37199a56e018eb2501e4225f08e00e` |
| H31 ramdisk | 8,537,600 | `d5c02b0fc2af3d4ee5415b4937477fb3dfa7712d211371c3343e287048c422f6` |

A and B are byte-identical. The exact kernel blob and embedded kernel Image
match H30, the H31 banner is present, and the H30 banner is absent. The receipt
selects only boot/init/helper/ramdisk and keeps `candidate_authority=false`.

## Public validation

`tests/test_a90_stock_rebuild_1007_h31.py` compares every functional leaf with
H30 and, when private output is staged, verifies A/B, boot, kernel, banner, and
receipt bindings. H31 remains H0-only and whether it boots remains unproved.
