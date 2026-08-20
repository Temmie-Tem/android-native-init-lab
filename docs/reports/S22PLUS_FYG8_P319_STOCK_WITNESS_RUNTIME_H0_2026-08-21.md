# S22+ FYG8 P3.19 stock-witness runtime and candidate-build closure H0

Status: **IMPLEMENTED_REVIEW_PENDING; H0 ONLY; NO LIVE AUTHORITY**

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

This unit turns the reviewed stock-emitter design into a deterministic,
diagnostic-free runtime source bundle and an optional host-only candidate-build
closure. It performs no device, ADB, USB, Odin, transfer, recovery, replay, or
live action. The Phase-1 output remains source/input-only; the separate Phase-2
output exercises the already reviewed userspace and boot/AP packagers without
granting qualification or F1 authority.

## Stock profile

The runtime is generated from the exact reviewed P3.18 sources and does not
consume the unqualified patched Max77705 driver sources. It has a distinct
`S22PLUS-FYG8-MAX77705-STOCK-V1` domain, encoding `4`, payload ABI `3`, and
`status_width=3`. Its ordered witness chain is exactly:

`irq -> initial_status -> classification -> probe`

The initial emitter stores only the three source-emitted bytes
`USBC1/USBC2/BC`; it never pads or claims bytes 3/4. The parent `0x23` readback
and W5 are explicitly unavailable. The two enhanced markers (parent unmask,
the alternate classification form, and the deferred seven-register line) are
grammar contradictions rather than silently accepted evidence. Complete,
incomplete, and ambiguous states use the unused details `0x6724`, `0x6725`, and
`0x6726` respectively. A compiled C fixture executes the encoder and the
publisher, including its exact Carrier progress/terminal positions 105/106.

The reachable P3.18 prefix retains gadget creation, role setup, UDC bind, and
the bounded direct host-state window. The inherited provider/diagnostic tail is
cut before `p317_capture_policy`; the stock publisher uses its own
`p319_stock_bypass_to_pair`, never calls a `p316_` helper, never opens I2C, and
publishes only the new stock envelope before parking. The diagnostic module is
absent from both the source path and final package.

## ABI and module closure

The auditor binds the exact fixed P3.10 Image
`71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8`, the P310
symvers `fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19`,
the loader `same_magic`/`check_modinfo` source and the P311 clean base boot
`58b38211d19ead1b0fe54e9fde463aef2c6dbf248be8d669e1b5415f244af17d`.
`__kcrctab`, `__kcrctab_gpl`, and `__ksymtab_strings` are directly equal between
vmlinux and Image; normal/GPL `__ksymtab` name/namespace PREL32 fields match,
with only the expected 31/28 value-field differences. The loader rule binds
the exact stock vermagic suffix after the first release token and records that
full release-token equality is not required; the fixed `finit_module` path is
the flags-zero path.

The exact 73-row plan renders EUD at index 38. Load-order resolution is
`3,566/3,566`: 3,238 fixed-Image providers and 328 earlier-module providers,
with zero duplicate, ambiguous, or missing providers. The input is the
no-clobber private 73-module snapshot produced by the preceding Phase-1
materialization (`...-20260821-06/module-bytes`), so this auditor has no
unstable `/mnt` module-tree dependency. All 73 module bytes are materialized
under private logical snapshot names; the package overlay is a
separate, deliberate four-member delta, not a copy of the full plan.

## Phase-2 host-only build

Phase 2 compiled A/B and a third verification copy of the static userspace.
The `init` is 79,888 bytes SHA-256
`34e78e7f5a6389f5f62cff2281f496043956122c4fe79b204d93070f3fed2160`; the
child is 1,384 bytes SHA-256
`3a9b561051f13d07dfb3fa9f75374ac06436e3e98f13cf28a43d80f7f17bef8f`.
All three compile identities agree, and the child is explicitly replaced in
the packaged ramdisk rather than leaving the 720-byte P311 child in place.

Each A/B candidate starts from the exact P311 clean base. The base is checked
to contain no generic `lib/modules` entries and no latch/diagnostic members.
The final ramdisk contains exactly these four generic-module members:

- `lib/modules/s22plus_dwc3_event_latch.ko`
- `lib/modules/spu_verify.ko`
- `lib/modules/mfd_max77705.ko`
- `lib/modules/pdic_max77705.ko`

The inherited 69 stock modules remain vendor-layer inputs and are not copied
into the generic ramdisk. Final unpack checks compare every four overlay bytes,
the replacement child, the fixed Image, and the absence of the diagnostic.

The Phase-2 A/B bytes are identical:

| artifact | size | SHA-256 |
|---|---:|---|
| `boot.img` | 100,663,296 | `b88f413d9baaa55b33c9880e6cb318f7a073e9b3ad0377ec810da6b9cfb458a5` |
| `boot.img.lz4` | 27,470,264 | `ae8d5af5642166a4a5fd46f7f72e8489cd845da2c32f40aa892a24a60c5186a6` |
| `odin4/AP.tar.md5` | 27,473,961 | `31cff51ae3f2ab4da4365f1cea6b127e3a136aaab21a5dc0ea4d989835a4b753` |

The AP contains only `boot.img.lz4`; its internal MD5 trailer and LZ4
round-trip are independently checked. These are private host artifacts, not
transfer inputs or live authority.

## Receipts and validation

The current no-clobber Phase-1 receipt is
`workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-08/result.json`,
54,193 bytes, SHA-256
`bd94a638a07a25b8ac400d94edc4ef8ced7749d48c9aebf4044db470adaf6ab8`, mode
`0400`, link count one. The separate Phase-2 receipt is
`workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-09/result.json`,
65,030 bytes, SHA-256
`231316f0569a9b06430d14211cc50dae0874583eccc7c5f5aef32aaa4bd855f7`, also
mode `0400`, link count one. The bound auditor is 80,958 bytes SHA-256
`5b03eb6fe89aeeb05e6ed0cac1abeb056c8b2cda8e31ea0a29d30b09fe903909`.

The earlier no-clobber `-06`/`-07` receipts remain preserved superseded
evidence: they bind the pre-snapshot-path auditor (80,958 bytes,
`666806db98253d68d4a373c8c2d0a433f55b2d32fede1fc78787ff7b2f954cf5`) and are
not overwritten or reused as current authority. The current `-08`/`-09`
receipts bind the 80,870-byte `5b03eb6f` auditor after the pinned private
snapshot source repair.

Both receipts regenerate through `--audit-only` without modifying existing
outputs. Focused stock-runtime tests pass 13/13, including hostile enhanced
markers, C encoder states, C publisher positions, no-clobber, and Phase-2
artifact audit. Relevant plan/materialization/parser/Carrier predecessor tests
pass 94/94. Python compilation and `git diff --check` pass for this closure
before any
commit.

## Boundary

This row remains review-pending and opens the new `stock-witness-runtime`
review topic. Independent changed-closure review must inspect the source
transform, fixed Image/loader binding, 3,566 import resolutions, clean-base
four-member overlay, child replacement, deterministic Phase-2 receipt, and
the no-device boundary. Even after review, a separate exact candidate intent,
qualification, and attended approval remain mandatory; this unit creates no
D0, D1, F1, recovery, replay, or live authority.
