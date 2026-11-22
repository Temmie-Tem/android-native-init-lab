# S20+ UniLoader failure analysis and retained boot stages

Target `SM-G986N / y2q / y2qksx / G986NKSS8IYC2`.

## Corrected candidate outcome

The retained Odin stdout shows `boot.img.lz4`, 100% and connection close
for both the candidate and original Magisk rollback. Both stderr captures
are empty. The candidate observer ran for approximately 180 seconds and
closed `NO_PROOF` with the exception class `Stop`. There is no candidate
root or FDT capture and no per-poll USB or readiness history. The record
does not distinguish absent ADB, offline ADB or Android that did not meet
the readiness predicates. The original Magisk image booted after physical
Download recovery and passed UID 0, Magisk 30.7, SELinux Enforcing and
FDT marker absence on the same boot. [Corrected run timeline](S20PLUS_G986N_UNILOADER_ANDROID_F1_2026-11-22.md#corrected-ap-result)

The candidate and rollback decode to 64 MiB Android v2 boot images. The
candidate embeds the exact original vendor Image at +2 MiB and preserves
the compressed Magisk ramdisk, Samsung DTB bundle and original boot
header outside the kernel size and image ID. The ARM64 runtime extent
grew from 70,512,640 to 72,609,792 bytes. Odin ends its observation before
the bootloader's subsequent load, jump or rejection.

ABL acceptance, wrapper entry, CPU/FDT guard, FDT clone and vendor
kernel/initramfs progress remain open. The original wrapper sends every
early rejection through the same silent `wfe` loop. All six retained
merged DTs have `/memory/reg` placeholders and no supplied initrd
pointers. The earlier positive ARM64 qualification supplied both in its
fixtures. The real ABL-supplied values and wrapper load address remain
unknown. [Original H0 image report](S20PLUS_G986N_UNILOADER_ANDROID_H0_2026-11-22.md)

The active read-only pstore D0 verified rooted Android continuity, the
ramoops backend and a pstore mount. The three old-record metadata paths
returned `unavailable`. Its six host commands performed no device writes,
reboot or log-body reads. Receipt SHA-256 is
`23aac71c29741f910645da4df6dac311fac003c9e4f05dcaa4465ac77b98c219`.
[S20+ pstore readiness contract](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-pstorepmsg-readiness-d0)

## Candidate stages

The H0 image preserves the existing CPU entry, pre-stack guard, vendor
Image, ramdisk and bundled DTBs. After the original guard passes, the
helper validates the incoming FDT's exact ramoops geometry, RAM-bank
containment and separation from the initrd, FDT and other reserved
ranges. If the slot fails those checks, the helper takes the ordinary
FDT marker and handoff path without a trace store.
[Stage producer](../../workspace/public/src/mainline/s20plus_y2q_h0/uniloader_stage_fdt.c)

| Record | Meaning after exact first-return observation |
| --- | --- |
| `guard-passed` | UniLoader passed the CPU and pre-stack FDT guard and admitted the record slot. |
| `fdt-marked` | UniLoader cloned the incoming FDT and inserted the build marker. |
| `handoff-ready` | UniLoader packed the final FDT and reached the point immediately before returning to the vendor branch sequence. |
| Tagged `Kernel command line:` | The vendor kernel reached that printk and the candidate console backend retained the line. |

The first three records form an ordered build-tagged prefix in the stock
ramoops PMSG slot. The candidate replaces the previous PMSG header and
a short payload prefix. Its cloned FDT reserves that tail and gives the
candidate driver the original dump, console and ftrace spans with PMSG
disabled. The original Magisk kernel uses its full layout again on return.
Its persistent RAM reader can publish a valid prior header and payload
as an old pstore PMSG file if the bytes survive the return path. The
candidate adds the build tag as the first boot argument on a bounded valid
command line. The host decoder accepts the exact ordered PMSG prefix and
the unique matching console tag, including Samsung's printk process prefix.
[Host decoder](../../workspace/public/src/mainline/s20plus_y2q_h0/build_uniloader_stages.py)

The recovery route must preserve RAM and the first returned boot must
expose the records for either witness to be observed. The active D0
covers metadata. A future connected collector must bind the exact
candidate, first returned boot and fixed files, with bounded output and
original Magisk health and FDT-absence checks. Its output can be limited
to the matching tag and stage result. If both records are absent,
pre-guard failure, an unavailable slot, lost RAM and unavailable
collection remain possible.

## H0 qualification

The freestanding ARM64 ELF is statically linked with no relocations.
The actual Image passed 15 QEMU cases. They cover six merged Samsung
DTB/DTBO fixtures with synthetic ABL memory and initrd placement on EL1
and EL2, two pre-trace rejections, five unsafe-slot fallbacks and two
stops between completed publications. The fixture read the PMSG bytes
with the stock header and ring-copy rules, checked the modified FDT,
preserved the input DTB and actual Magisk initrd, and stopped at the
unchanged vendor entry. Separate fixtures exercised console parsing.
[ARM64 qualification](../../workspace/public/src/mainline/s20plus_y2q_h0/qualify_uniloader_stages.py)

A development VM run exposed an alignment data abort in the new
command-line copy. The final code uses byte copies and was rerun from
a fresh build. Independent exact-source H0 review returned `PASS_GO`
with no outstanding findings. The alignment finding concerns the
successor development build.

Private build, VM and AP verification evidence is under
`workspace/private/outputs/s20plus-y2q-uniloader-stage-h0-20261122-final/`.
The successor AP contains one `boot.img.lz4` member, passed MD5 and
decoded boot verification, and passed the pinned Odin parser with USB
and network hidden. Its SHA-256 is
`e7a3353821f39ab1d3e71a09e416f8e1f0cc8f266289cce9f707f489a2a0c9b7`.
The verified original Magisk rollback AP SHA-256 is
`1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`.
The corrected-run byte comparison receipt SHA-256 is
`31a12004f58e59b6ca6c9aaeac5c84364c73abe6966b5e76d6793db5f9cf66f9`.
This was H0 preparation plus one bounded D0 read. Candidate dispatch,
new device authority, partition access and S22+/A90 commands were zero.

## Attended first-return owner

The captured host pair is pinned to the stage AP and verified original
Magisk AP above. The successor owner exact-loads the previously reviewed
compatibility owner in isolation and reuses its target lease, Download
arrival, consumed-claim ledger, process cages, and one-shot recovery.
The new activation binds both relevant target sections, the exact owner
and reader, the selected pair and the focused tests. The older
compatibility owner's activation still validates.
[Stage F1 target contract](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-uniloader-retained-boot-stage-attended-f1)

Once the owner has proved original rollback and fresh final rooted
Android health, the new read compares the build-bound pattern in only
the two fixed pstore files. It checks the same boot before and after
and verifies candidate FDT absence before opening records. The private
capture contains compact classifications and the boot digest. It does
not export pstore bodies. A failed or cut scan carries no retained-stage
claim and does not authorize replay. The inherited final FDT absence and
rooted Android checks still control healthy closure. Signatures from a
later observed boot are outside this read.
[First-return reader](../../workspace/public/src/scripts/revalidation/s20plus_g986n_uniloader_return_pstore.py)

Host validation checked the APs and retained physical Download recovery.
The focused regression run passed 46 tests, including a captured shell
fixture, a failed record producer, malformed and stale markers, and a
direct check of exact reader argv at the inherited dispatch fence.
An independent review returned `PASS_GO` with zero outstanding findings.
The reviewed owner was activated through its single boolean change and
the separate canonical activation record SHA-256
`6a46c27aab9f769e8527b40ddfa051a47da7f698918af18c816570e8ac9c3f6d`.
Active host closure validation passed before connected preparation.
The new connected D0 root-health receipt before preparation is
`3fd12f249b6ed814ef6553fce1b12899a0fdf27ac3caaa24356f3247eff3aa08`.
The stock Android shell and command flags used by the reader are covered
by these primary reference sources.
[AOSP mksh pipefail conformance](https://android.googlesource.com/platform/external/mksh/+/2e46594a0b7f5014d1a6751020dabe80e576c954/src/check.t)
[AOSP Android 13 Toybox flags](https://android.googlesource.com/platform/external/toybox/+/refs/tags/android-13.0.0_r28/android/device/generated/newtoys.h)

Connected preparation proved fresh original rooted Android and FDT
marker absence, then proved Download arrival at the same physical USB
topology. The exact prepared record was published at 23:03 KST on
November 22 and expires at 23:18:12 KST. Prepared receipt SHA-256 is
`1318ca5842ab2b4b5ad2ca158923b3b793f0866f50b902cca86bd06af1cbe3f0`.
At this checkpoint the stage owner held the S20+ guard and awaited the
operator's approval. Candidate and rollback transfers, pstore record
reads, and commands to S22+ or A90 were zero.
