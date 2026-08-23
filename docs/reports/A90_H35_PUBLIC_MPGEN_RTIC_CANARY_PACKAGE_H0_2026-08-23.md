# A90 H35 public-MPGen RTIC canary package — H0

Date: 2026-08-23
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 private-host packaging and static validation
Device, `/dev`, USB, ADB, and network contact: none
Other targets: untouched
Authority: none — no D0, D1, F1, approval, ordinal, journal, transfer, reboot,
rollback, or replay is created here

## Result

The fresh host-only successor identity is:

- version `0.11.202`;
- build `phase3-minimal-h35-public-mpgen-rtic-canary`;
- cycle `H0-PHASE3H35`;
- enable path `/cache/a90-auto-handoff-phase3-minimal-h35.enable`; and
- latch path `/cache/a90-auto-handoff-phase3-minimal-h35.done`.

Two independent flat-builder branches produced byte-identical H35 boot images:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| H35 A `boot.img` | 58,372,096 | `5e2a44420195090e75f63e350cacdbcad88710e77cef9bcf29a6d3ee6f4ad759` |
| H35 B `boot.img` | 58,372,096 | `5e2a44420195090e75f63e350cacdbcad88710e77cef9bcf29a6d3ee6f4ad759` |
| A/B receipt | 5,430 | `5c21ec82cee9cc9497867518d710c8374b54240bf115f3e2b9c3d0ed5b4216f9` |

The receipt records `byte_identical=true`, `accepted_boot_unchanged=true`, and
`candidate_authority=false`. Its artifact namespace contains only `boot`,
`init`, `helper`, and `ramdisk`. These are host artifacts, not permission to
send the boot image.

## Fresh identity allocation

Before allocation, current-tree and Git-history searches returned no earlier
`phase3-minimal-h35`, `0.11.202`, or H35 A90 identity. The immediately preceding
sequence was H30/H31/H32/H33/H34 at versions
`0.11.197/0.11.198/0.11.199/0.11.200/0.11.201`.

H29 through H34 remain consumed and non-replayable. This allocation neither
reclassifies their outcomes nor establishes current V2321 health. The tracked
terminal remains `RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED` until a future
fresh connected read establishes otherwise.

## Reviewed kernel input

The already-final hazard review is
`A90_RTIC_PUBLIC_MPGEN_CANARY_HAZARD_INDEPENDENT_REVIEW_2026-08-23.json`,
SHA-256
`d180b3637bb36eefce7c28251a8c17ddb73393068135b4dff16972e5f86a8c94`.
Its verdict is `PASS_GO_H0_CANARY_HAZARD`, accepts H1–H6 for one future attended
canary only, records `candidateAllocated=false` and `liveAuthority=false`, and
leaves every ordinary candidate and live prerequisite fresh.

The exact carrier was assembled without rebuilding or modifying any selected
component:

| Ordered component | Bytes | SHA-256 |
|---|---:|---|
| `UNCOMPRESSED_IMG` header | 20 | image size encoded little-endian |
| reviewed raw `Image` | 48,830,480 | `1ddae56f8df97030794a590192e4a4162876736029b1a54fd26173c9287002b7` |
| stock hardware DTB 0 | 497,331 | `c835c124f96525da3a07acf055b3ac5e8e8b5771d363406d9e962351643159c8` |
| stock hardware DTB 1 | 499,609 | `575a327417b6bc3f33b1ffedd56292396a9b264f9a1e0c674f69df586ec05603` |
| generated RTIC DTB | 173 | `68e6ab5bb2ccdde5e3d87086110257176c0fe55726d1d4f5db6eba3a4b6aca04` |
| complete carrier | 49,827,613 | `15b49a71aeb2342a5b5a7e24de27f78a4124bf877f6d8d8f28aaab928fa6bd71` |

The complete carrier reproduces the hash accepted by the hazard review.
`a90_rtic_mp_consistency.py` returns `PASS`: three FDTs at exact offsets, one
RTIC FDT, one `MP_DATA`, interface `30.3`, MP VA
`0xffffff8009f00000`, raw offset `0x01e80000`, size 1,624, and expected/actual
MP SHA-256
`d95fd9710dd019c5f2e0a273669bcb9b96f81dfdf994afd940b9abb4ff04ec69`.
This is structural self-consistency, not stock producer equivalence or a boot
result.

## Base boot construction

The prior exact-toolchain base boot was unpacked with the pinned public
`unpack_bootimg.py`. Only its kernel argument was replaced with the exact
carrier, and it was repacked with the pinned public `mkbootimg.py`.

| Surface | Before | H35 base |
|---|---|---|
| boot bytes | 66,379,776 / `5cf27a56b7887b3f766af3caa7c1441cac51d153faf4f64a771902ad7f0118f6` | 66,379,776 / `5d681bbddf527fdacf1e433cdf30a0ca0b11d455c1b6e879c809418fd0d75484` |
| ramdisk | 16,545,280 / `245c135c34d66b067e17f459fc0ee17f3f0d03be8024289df038a590f18d6eba` | byte-identical |
| kernel | stale H34 carrier | exact `15b49a71…` carrier |
| mkbootimg semantics | header v1, page/offsets, board, cmdline, OS version/patch | equal except payload paths |

Re-unpacking the new base recovered the exact carrier and unchanged ramdisk.
The no-clobber private packaging receipt is
`workspace/private/work/a90-h35-packaging-20260823/package-receipt.json`,
SHA-256
`6809b218732277567af7709e9a260bc3663f33bfe7a8a12beca648fc09dd20a0`.
Private paths and bytes remain untracked.

## Identity-only ramdisk package

The H35 manifest is
`workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h35/manifest.toml`:

- manifest SHA-256
  `0b8ed49e5cb4ddc57fb73a1f43948d2c0c93829d7fb71a751f9badf75b52d89a`;
- effective-manifest SHA-256
  `9fa94d1ad72c4891da036638a7ac43127a008cd45869df3b54f1fb0b8cf252b9`;
- init closure SHA-256
  `3d1514e3f266e5b77886bf4511a396c9328b487b0c614c3c79fd3df16d26ca52`;
- accepted historical boot SHA-256
  `0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3`;
- observer public-key SHA-256
  `d9f0fe0db6a4d1572c4cca5744df707a61d1525d1ef2901c6eb6d03ffea11133`;
  and
- `candidate_authority=false`.

After removing only `profile`, `cycle`, `decision`, `random_seed`, the base-boot
path/hash, the four version/build/enable/latch flags, and the first validation
banner, the effective H35 manifest is exactly equal to H34. An adversarial
extra cflag is rejected by the public test. Thus the ramdisk execution
semantics are inherited; the only intended ramdisk changes are the fresh H35
identity and state paths.

The independently built H35 artifacts are:

| Flat-builder artifact | Bytes | SHA-256 |
|---|---:|---|
| static AArch64 init | 1,723,376 | `fbf330683ee08958379e0f69d2795d6dd26530b8cb1f6eb860e131fe959f4c00` |
| static AArch64 helper | 1,649,904 | `fcb005b0454aceb08aa6f8f81d83aa303e37199a56e018eb2501e4225f08e00e` |
| packed ramdisk | 8,537,600 | `194a8797f59b7b0360845b6daa02d303bb2c09d2f6271116a10d9f1835feb824` |

Re-unpacking the final boot image returns the exact reviewed carrier. The init
contains the H35 banner and H35 enable/latch paths and contains no H34 banner.
The helper, init, ramdisk, and boot bytes are pairwise identical across A and B.

## Validation and remaining boundary

Public checks cover fresh identity, exact effective-manifest reuse, exact
hazard binding, false authority, and hostile carrier/cflag changes. Private
checks additionally bind the base, A/B images, internal carrier, raw Image,
init, helper, ramdisk, receipt, and compiled H35 strings.

This report freezes packaging evidence only. A package-specific independent H0
review is still separate. Even a later review pass cannot create qualification,
a candidate manifest, a current owner/continuation/observer/rollback binding,
fresh V2321 health, physical-recovery proof, approval, or F1 authority. The
next legal sequence is package review, then candidate-specific qualification
and manifest preparation, then fresh connected D0 and one attended exact
approval. No device step is performed here.
