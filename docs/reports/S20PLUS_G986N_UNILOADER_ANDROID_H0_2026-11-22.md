# S20+ G986N UniLoader rooted Android control

Target `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`.
The first physical success criterion is healthy resident Magisk Android and
a fresh loader marker from the same candidate boot, followed by restoration
of the original resident boot and final health. The host-only build and
ARM64 handoff tests completed. Physical boot, return and F1 activation remain
open.

## Image design

The [builder](../../workspace/public/src/mainline/s20plus_y2q_h0/build_uniloader_android.py)
pins the already-proved resident Magisk boot and MagiskBoot tool through the
existing S20+ resident input declarations. The y2q adapter compiles the
libfdt, string and memory routines from [UniLoader revision 7781b33](https://github.com/ivoszbg/uniLoader/tree/7781b33c87ccde3e57bb744c5b8bccdbedfa4bc3).
Its outer Android v2 image keeps the compressed Magisk ramdisk and bundled
Samsung DTBs byte-identical. Header fields other than kernel size and member
checksum match the resident boot. The repack produces a 64 MiB private
`boot.img` with an AVB footer. Its modified payload's acceptance by the
exact physical ABL remains unobserved.

The ARM64 entry uses the resident Image's 512 KiB text offset and physical
relocation flags. The wrapper embeds the exact resident Image at a 2 MiB
relative offset and extends the advertised runtime extent accordingly.
The stack and FDT scratch stay inside the file-backed prefix. The loader
branches directly into the embedded vendor Image. This requires no Image
copy or fixed physical destination imported from another board.

Before any store, the assembly entry checks CPU state. The compiled leaf
guard bounds the ABI-provided incoming FDT and checks the wrapper/kernel envelope
against its RAM banks, incoming FDT, inherited initrd, memreserve table
and fixed reserved-memory nodes. It retains Linux-allocated dynamic pools.
With an admitted tree, the loader adds one build-specific
`/chosen/codex,y2q-uniloader-android-v1` property to a clone and passes that
clone to the original kernel with x1–x3 zero. The incoming tree and initrd
are read-only inputs.

## Evidence

- The build used both the exact retained raw vendor Image and the resident
  boot's original DTB bundle. Offline comparison checked the embedded
  Image, compressed ramdisk, DTBs and preserved header bytes after repack.
  The cross-built ELF has no relocations. The compiled guard disassembly
  covered 974 ARM64 instructions without stores, stack use or calls.
- QEMU with GDB stopped at the actual embedded vendor kernel entry with
  all six retained boot DTB and Korean DTBO combinations. The fixtures
  provided RAM and initrd pointers and exercised EL1, EL2 and two wrapper
  load addresses. In every case the marker matched, the input FDT and
  initrd bytes were unchanged, and removing the marker yielded the
  original tree semantics. The fixtures stop at the first vendor instruction.
- Four additional actual ARM64 cases stopped at the loader rejection
  point with the stack and scratch still zero. They covered EL3, an
  inherited initrd overlap, a fixed reservation overlap and a preexisting
  marker.
- The current fixed S20+ Root-Health D0 made one host inventory
  invocation. Its exact selector found one plausible row that failed the
  required target and healthy transport predicate. No selected-target
  or root commands ran. S20+, S22+, A90 and other-target device command
  counts and device effects are zero. The closed failure receipt SHA-256 is
  `d475bdfad42ebbf1e78280bbbf1ec7fa11d7b7dd0b68c6dfc292792971d0e066`.

The actual ABL wrapper entry address, live FDT memory banks and initrd
extent remain unconfirmed. The real-device test requires the target's
independently reviewed exact boot-only owner, marker read bound to the
same boot as rooted Android health, original-resident rollback,
physical Download recovery and the finite attended grant. The live
health reader currently covers rooted Android health only. This unit
adds no connected reader or device owner.

Private evidence is under
`workspace/private/outputs/s20plus-y2q-uniloader-h0-20261122.sgJEum/`.
The final build and source receipts are in `control-3/result.json`
and the raw QEMU/GDB cases are in `vm-release/`.
