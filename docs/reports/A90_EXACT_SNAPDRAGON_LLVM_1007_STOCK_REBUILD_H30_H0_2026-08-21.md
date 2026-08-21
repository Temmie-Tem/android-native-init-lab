# A90 exact-toolchain H30 identity-only materialization — H0

Date: 2026-08-21
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only build/materialization
Device contact: none
Authority: no D0, D1, F1, token, approval, or live authority

## Result

H30 was materialized from the same exact-toolchain functional configuration as
H29. Only version/build/cycle, random seed, and fresh enable/latch identities
changed:

- version `0.11.197`;
- build `phase3-minimal-h30-stock-rebuild-1007-cfp`;
- cycle `H0-PHASE3H30`;
- `/cache/a90-auto-handoff-phase3-minimal-h30.enable` and `.done`.

The base boot, complete non-identity cflag set, init closure, helper, kernel,
kernel Image, and validation strings after the banner are unchanged from H29.
`candidate_authority = false` remains explicit. H29 remains consumed and is not
replayed or reclassified.

Whether this kernel boots A90 remains unproved. This report creates no F1
manifest, approval, token, connected preflight, or device authority.

## Exact bindings

| Item | Size | SHA-256 |
|---|---:|---|
| H30 manifest | — | `cd067d0000c3f64d9367b5f5b0f6c29202829367a8dc9e4f81b886dfe8565ef5` |
| H30 effective manifest | — | `b92a41aebeea2bbfdfd0b91fe708135ebcc124dafd00b5ef8c52c70b9744bb22` |
| H30 A/boot.img | 58,372,096 | `d28bd41434d252619dd95ecb352f55140d93889fd599784c0a7dbf491959c5fe` |
| H30 B/boot.img | 58,372,096 | `d28bd41434d252619dd95ecb352f55140d93889fd599784c0a7dbf491959c5fe` |
| A/B receipt | 5,426 | `88de4c342d66025bc49689a1c6b3c3d6fed86f418eb063010ce0dc06dea31f4f` |
| exact kernel blob | 49,827,613 | `59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac` |
| kernel Image | 48,830,480 | `6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557` |
| H30 init | 1,723,376 | `6daf9b86e1d7804c3c161a7e23ec8789f6c6b460783431c7fac098b3aa279275` |
| helper | 1,649,904 | `fcb005b0454aceb08aa6f8f81d83aa303e37199a56e018eb2501e4225f08e00e` |
| H30 ramdisk | 8,537,600 | `eb4094d31ca94294c3ad34612dbd3185e712b455aebd2a1478dc68156c3bcfd9` |

The H29 candidate SHA-256 was
`c3d1b84eab65f387ce807cf9c355dc04dcc966cef15bf64e4fda901242907324`;
H30 is byte-distinct. Private output is staged under
`workspace/private/outputs/a90-h30-stock-rebuild-1007-cfp-ab-20260821-01/`.

## Validation

Flat-builder audit and deterministic A/B build passed with the staged observer
public key and unchanged accepted base. A and B are byte-identical. The packed
boot contains the exact expected kernel and H30 banner, excludes the H29
banner, and the receipt selects only `boot`, `init`, `helper`, and `ramdisk`.
Focused H30 validation is `6/6` with private checks active. No device command or
live preparation was performed.
