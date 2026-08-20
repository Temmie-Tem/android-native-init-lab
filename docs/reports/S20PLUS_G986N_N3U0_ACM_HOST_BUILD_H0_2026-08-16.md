# S20+ G986N N3-U0 ACM host build H0 report

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`)

Status: **PASS HOST BUILD - REVIEW PENDING - NOT LIVE AUTHORIZED**

Machine review state: `REVIEW_PENDING`; live authority: `false`.

## Scope

This unit implements the smallest S20+-specific native USB witness selected by
the preceding H0/source and D0 substrate report. It is a temporary Magisk
`overlay.d` boot addition, not a PID1 replacement, kernel/DTB change, module,
network/storage gadget, persistent promotion, or connected execution.

The build performed no ADB, USB observation, `su`, reboot, Download transition,
Odin invocation, or partition transfer. A90 and S22+ supplied architectural
lessons only; their artifacts, identities, commands, and authority were not
used.

## Frozen public sources

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/native-init/s20plus_n3u0_acm_witness.c` | 18,286 | `cb6b71b08575658edc22bb00472ee13eaa8198543ad393ef6e4ad6efb22ef2f1` |
| `workspace/public/src/android/s20plus_n3u0_acm.rc` | 368 | `bbaab9cc2829119d5a90775456eb0935b0890b1a3ce0e418afc847cc346385ad` |
| `workspace/public/src/scripts/revalidation/build_s20plus_n3u0_magisk_overlay.py` | 22,454 | `93af2c760acd7d4f33a992fe68cb0346485aa675490aed6c43b993f1f09dcce2` |
| `tests/test_s20plus_n3u0_magisk_overlay.py` | 12,470 | `5e95b63ab9562a18069b8f241ec789e096f2d73be40d7379bdeecaa62538d57b` |

The builder also records the exact existing same-target H0 helper closures:

- common S20+ static-build helper SHA-256
  `bcbbc60052631d810ffa3f866e7077fdbc394f161c701d00f17d9c1a3166c0cc`;
- S20+ boot-only packaging helper SHA-256
  `0ba7df69fefc72392750094a63896dd903f005c4b60eacf752b4ac345770c577`;
- Magisk v30.7 `magiskboot` SHA-256
  `a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e`.

## Exact base and ramdisk delta

The base is the already-known healthy resident Magisk boot, 67,108,864 bytes,
SHA-256
`d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc`.
An unpack/repack with no change reproduced that byte stream exactly.

The builder preserved the kernel, DTB, header, Magisk `/init`, and all existing
ramdisk entries. The complete listing delta is exactly:

| Added entry | Mode |
|---|---:|
| `overlay.d/s20plus_n3u0_acm.rc` | `0644` |
| `overlay.d/sbin/s20plus_n3u0_acm` | `0750` |

No entry was removed or replaced. `magiskboot cpio test` returned the expected
Magisk state `1` both before and after the addition.

## Witness behavior

The rc starts the disabled one-shot service only after
`sys.boot_completed=1`, in explicit `u:r:magisk:s0`. The static witness accepts
no caller argument and performs one finite state machine:

1. require configfs at `/config`, one exact UDC `a600000.dwc3`, the stock `g1`
   gadget bound to it, and no pre-existing owned gadget;
2. re-read the stock UDC immediately before unbinding it;
3. create only `/config/usb_gadget/s20plus_n3u0` with one `acm.usb0` function;
4. re-check that stock remains unbound before binding the owned gadget;
5. read the owned function's exact one-digit `port_num`, accept only `0..3`,
   and derive `/dev/ttyGS<n>` from that value;
6. emit only the fixed `S20PLUS_N3U0_ACM_V1` banner in a bounded 40-attempt,
   250-ms loop; and
7. unbind/remove only the owned gadget and restore stock `g1` to the exact UDC.

This avoids the false assumption that the new function always receives
`ttyGS0`; the stock gadget may already reserve port zero. The candidate makes
no `mode=peripheral` write. A busy or changed controller therefore stops and
restores rather than widening the first experiment.

Every invocation of the stock-unbind boundary makes stock restoration
mandatory, including a write-success/readback-or-close-failure return. Owned
cleanup additionally runs after any owned-gadget touch. SIGTERM, SIGINT, and
SIGHUP request the same cleanup path. An
unmaskable process death, kernel failure, or power cut cannot be closed by
userspace cleanup; the future attended live process must treat that as boot
failure and use the exact resident-boot rollback rather than replaying this
candidate.

## Host validation

The witness is a 597,752-byte stripped static AArch64 ELF with no interpreter,
`DT_NEEDED`, undefined symbol, or writable-executable load segment. Its
SHA-256 is
`a0d90dbba2fe6f85af2421f888ecdfd76ecf22420b03846260ecab708de4810d`.

The compiled-in host state-machine selftest exercised the success route and
all seven injected operation failures. It proves that no restore is attempted
before the unbind boundary, that an uncertain post-effect unbind failure still
invokes stock restoration, and that every failure after touching the owned
gadget invokes both owned cleanup and stock restoration.

The focused hostile Python suite passes **11/11**. It covers:

- frozen source and output identities;
- two byte-identical witness builds and two byte-identical full artifacts;
- exact two-entry ramdisk delta and preserved Magisk `/init`/kernel/DTB;
- static ELF closure;
- one-member boot-only TAR plus Samsung MD5 trailer;
- missing SELinux service label and forbidden mode-write source mutations;
- wrong base-boot substitution and output no-clobber; and
- absence of device/live execution commands.

## Canonical private outputs

Directory:
`workspace/private/outputs/s20plus_g986n/n3u0_acm_overlay_v1/`

| Output | Size | SHA-256 |
|---|---:|---|
| `s20plus_n3u0_acm` | 597,752 | `a0d90dbba2fe6f85af2421f888ecdfd76ecf22420b03846260ecab708de4810d` |
| `boot.img` | 67,108,864 | `7024d206453dbd82f04187b7a3ccb6042aef7e2e20ed9660a67b47ecf19206eb` |
| `boot.img.lz4` | 26,103,098 | `ee57ba63c557bca651fd633f77d6f006585ec0d5b22bb18418a6fade3590809d` |
| `AP.tar.md5` | 26,112,041 | `3aad497979cfa0f247aef68f50ea792f40127afa037c134eeb0d2e96798ca7af` |
| `manifest.json` | 11,916 | `594b83dfc52f37e1db21ab5f240b804ad10a8eb1d0642719aef0ecd5ddfc619f` |

The AP has exactly one regular member, `boot.img.lz4`. Packaging it does not
authorize Odin or a transfer.

## Remaining gates

This closure is not live-ready merely because it builds. Before a device boot:

1. independently review the frozen source, builder, tests, artifact identities,
   stock-gadget race handling, and target-contract interaction;
2. independently review the now host-implemented bounded USB observer recorded
   in `S20PLUS_G986N_N3U0_USB_OBSERVER_H0_2026-08-16.md`; it selects the exact
   product/banner without relying on a stable `ttyACM` number but remains
   dormant and creates no run authority;
3. define a fresh S20+-only attended boot process that binds this exact
   candidate and the exact known-good resident Magisk boot as rollback;
4. preserve candidate no-replay and treat absent banner as no-proof, not as
   permission to resend; and
5. require final exact healthy rooted Android after the temporary candidate is
   replaced by the resident boot.

No current R1/F1 approval or prior A90/S22+ result grants any of these gates.
