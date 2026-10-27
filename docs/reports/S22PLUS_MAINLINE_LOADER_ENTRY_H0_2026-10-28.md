# S22+ mainline loader entry and boot-v4 packaging

Date: 2026-10-28. Target: SM-S906N / g0q / S906NKSS7FYG8.
Status: **H0 BUILT AND QUALIFIED; NO PHYSICAL ENTRY OR ACTIVATION**.

The operator requested another Claude discussion and continuation of the next
unit. The retained kernel, DTB and RAM PID1/initramfs were reused unchanged.
This successor repairs the uniLoader entry/copy path and produces a checked
boot-only package. It does not register a candidate, open a device owner, change
host networking or contact a device. A90 and S20+ were untouched. The vendor
boot-journal prototype remains paused and its unrelated dirty files preserved.

## Decision and implementation

One tools-disabled Claude Opus 5.5 discussion reviewed sanitized source and the
known ABL uncertainty. Its advice was checked against the actual consumers.
Fixed staging remains the selected approach: it keeps later kernel/DTB/initrd
destinations statically checkable and avoids a new position-independent C
runtime. Initial ABL source placement is checked when the loader actually runs;
no guessed EFI address or fallback constant is treated as a live binding.

The [local patch](../../workspace/public/src/mainline/s22plus_canary_h0/uniloader-g0q-entry.patch)
and [builder](../../workspace/public/src/mainline/s22plus_canary_h0/build_loader.py)
make these changes:

- The Image header describes the complete runtime extent from `_head` through
  `_stack_end`. The 448-byte entry stub is explicitly first; `_start` follows it.
  Copying covers only the initialized body through `_file_end`, including the
  linked GOT. Source BSS/stack and bytes beyond the file are not read.
- The entry checks EL1/EL2, little-endian MMU/cache-off state, alignment and
  nonwrapping source-file bounds. Its private table admits the already-loaded
  image within retained RAM banks. Reservations separately constrain all fixed
  destination writes; a kernel reservation does not forbid reading the image
  which ABL has already loaded there.
- Equal placement skips copying. A higher destination uses a backward copy.
  A lower destination must end before the executing source header/stub; other
  overlaps park before any store. This rejection is not a watchdog or recovery
  claim and has no physical diagnostic channel in this candidate.
- DAIF is masked. DSB/IC IALLU/DSB/ISB sequences precede both relocated-code and
  kernel entry. The actual ABL normal path explicitly clears MMU/D-cache/I-cache
  state, but its late external calls and exact entry EL are not physical proof.
  The runtime guard preserves that distinction.
- All target C objects use strict alignment, general registers and disabled
  builtins. The assembly memcpy/memmove uses aligned words or exact byte tails.
  A failed DTB rewrite now parks before any kernel copy/jump.

The first local build caught a missing include for the fatal DTB path. The
next static qualification caught orphan GOT sections beyond `_file_end`; they
were explicitly included. An initially over-restrictive free-RAM source check
was changed to RAM-bank admission after independent review. All fixed write
destinations still exclude reservations. Failed build/qualification directories
remain private and were not relabelled as the final output.

## Evidence and limits

The final actual linked blob passed:

- **20 Unicorn cases:** same placement, both copy directions, overlapping and
  adjacent ranges, live-stub rejection with zero stores, alignment, non-RAM and
  overflow rejection, a page-exact source tail, entry-state predicates, complete
  loader execution to kernel entry and malformed-DTB stopping.
- **1,051 direct linked memcpy/memmove cases:** zero/small/tail lengths, all
  tested source/destination alignment combinations, both overlap directions,
  exact access bounds, return pointer and unchanged surrounding bytes. The
  historical real memcpy fails this corpus on an unaligned access.
- **Full-loader checks:** initialized BSS before C, stack within its reserved
  page, natural alignment, exact kernel/initrd destination bytes, exact DTB
  properties/reservations/version/boot CPU except declared initrd bounds, and
  the kernel argument registers and synchronization path.
- **Separate actual-EL QEMU tests:** the same unmodified blob, reset EL1 and
  EL2, reaches the relocated body with exact copied bytes. Reset EL3 rejects.
  GDB only reads state and sets hardware breakpoints; it does not change CPU
  registers to obtain these outcomes.
- The seven existing canary protocol/FDT tests and Python compilation passed.

Unicorn 2.1.4 reports EL1 despite changes to PSTATE mode. Its EL2/EL3 predicate
tests therefore explicitly inject the CurrentEL result, and the EL2 branch's
SCTLR read result; negative SCTLR cases inject the value at the real guard.
The separate QEMU results cover actual EL selection. Neither emulator proves
physical cache coherency, Gunyah stage-2 attributes, actual ABL placement,
inherited watchdog/charging behavior or physical USB/recovery.

## Boot-only package

The [packager](../../workspace/public/src/mainline/s22plus_canary_h0/package_loader.py)
reuses the existing magiskboot and deterministic boot-only AP machinery. It
replaces the outer boot-v4 kernel member with uniLoader in the exact original-A
96 MiB envelope. It verifies the remaining header bytes, outer ramdisk,
signature and retained AVB content, adjusted trailer geometry, LZ4 roundtrip,
and the sole `boot.img.lz4` AP member. Two independent repacks produce identical
boot and AP bytes. The original outer ramdisk is retained but uniLoader supplies
its own embedded initrd and DTB. Retained signatures do not authenticate this
modified payload; ABL acceptance remains a separate physical question.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| uniLoader | 44,461,952 | `d44bb09d5c3b5a52826471d4bf3bd7d0472b7f23e558d1665e3d157d756e7f3d` |
| boot.img | 100,663,296 | `f134f1c224261efb4e306a4c474aaf364e313d7469d30e677d57c99a80be6f8c` |
| AP.tar.md5 | 24,186,921 | `fadbfd2f6f69121a3d5509d70abed229a4d6a9ca4e7c685f6427716881089c67` |

The selected local LZ4 binary is explicitly pinned in this new H0 recipe; it
differs from an old P286 tool pin. No historical tool pin or active machinery
was changed. The first package attempt rejected that mismatch before writing
an output directory. QEMU's first entry-test invocation stopped before execution
because of a missing default NIC ROM; disabling unused default devices fixed
the test setup without changing the loader.

## Review, checklist and next unit

Independent review covers the changed loader source, actual ELF/raw geometry,
source-table semantics, fixed destination bounds, byte-level tests and entry
state evidence. Its final source-bound receipt is retained with this unit.
The Claude discussion is advisory and is not device-capability activation.

Past-failure checklist: **ABI — confirmed** by actual ARM64 instructions,
strict access checks and separate EL tests; **SEMANTIC/ROUTE — confirmed within
H0** by the real linked producer and explicit emulator limits; **ARTIFACT —
confirmed within H0** by ELF/raw joins and unpacked boot/AP byte checks;
**RETURN — unconfirmed for mainline**, no physical recovery experiment occurred.
No new permanent boundary, live gate, contract activation or grant is created.

The next bounded unit is to connect this exact mainline observer/package to a
reviewed finite attended execution/recovery owner, then perform the first RAM
USB canary with original-A return and final health. Existing FYG8-only readiness
and consumed approvals do not admit this new kernel. Its first physical success
still requires actual mainline PID1 and authenticated USB evidence. This work
does not resolve native_data's retained M=40 recovery state; storage remains
excluded from the canary.

Private evidence: `workspace/private/outputs/s22plus-mainline-loader-h0-20261028-1/`,
including `claude-review/critique`, `loader-5`, `qualification-4`, `entry-vm-2`,
`historical-memcpy-counterexample.json`, `package-1` and `review`. Before/after
Claude quota and per-call token records were appended to the private usage
ledger; the account-wide meter changes are distinct from per-call tokens and
the CLI's list-price estimate is not a subscription charge.
