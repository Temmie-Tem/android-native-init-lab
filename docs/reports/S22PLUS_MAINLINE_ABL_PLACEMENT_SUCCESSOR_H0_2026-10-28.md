# S22+ ABL placement conflict and minimal loader successor

Date: 2026-10-28. Target: SM-S906N / g0q / S906NKSS7FYG8.
Status: **H0 REPRODUCED AND CORRECTED; NO PHYSICAL SUCCESSOR EXECUTION**.

The retained FYG8 firmware's normal EFI placement conflicts with the original
uniLoader staging address. Under that path's 64 possible displacement selectors,
the actual old loader accepts only the identical placement and rejects the
other 63 before any store. Moving only the fixed staging address removes this
conflict while retaining the entry-state, RAM-range and live-stub guards.

This is a specific source/artifact compatibility defect, not a measurement of
ML001's actual placement, selector or failure point. The 64-case enumeration is
not a probability estimate. [ML001](S22PLUS_MAINLINE_ML001_RUN_2026-10-28.md)
remains consumed `NO_PROOF / ANDROID_CLOSED_HEALTHY`.

The user authorized the host analysis and successor preparation after the
[two-model discussion](S22PLUS_MAINLINE_BOOT_OBSERVATION_DISCUSSION_H0_2026-10-28.md).
No external-model calls, connected reads, device commands, registrations,
activation, grants or transfers occurred in this unit. A90 and S20+ were
untouched. Unrelated vendor boot-journal and ABL-report edits were preserved.

## Source-to-consumer chain

1. Reopened and hash-verified the retained FYG8 `LinuxLoader.efi` and `uefi.elf`.
   The latter contains a `uefiplat.cfg` **Kernel** region and the QcomBds producer
   of the `KernelBaseAddr` / `KernelSize` EFI variables.
2. QcomBds function `0x1280c` looks up the named region, then publishes its base
   and size through SetVariable. The producer and LinuxLoader GetVariable use
   the same GUID. Successful lookup/publication/read is an explicit assumption;
   no live EFI value was acquired.
3. LinuxLoader's normal BootLinux path calls `0x17500`, then `0x17890`.
   For this uncompressed ARM64 header with nonzero image size, `0x17500` adds
   the Image header's text offset to the EFI base. The retained loader's text
   offset is zero. The helper at `0x15430` obtains/caches a bounded selector and
   derives the displacement subsequently added by `0x17890`.
4. The resulting source envelope begins at the original loader's fixed staging
   address. Each nonzero selector puts the executing header/stub inside the
   downward-copy destination interval. The existing `.Lbelow` guard therefore
   correctly refuses to overwrite its own executing instructions.
5. The fallback path uses different constants when the EFI query fails. Those
   constants do not describe the successful named-region path. The predecessor
   review deliberately left successful EFI placement unknown; unpacking the
   variable producer and its configuration supplied the missing static input.

Exact region/selector values, disassembly, extracted firmware and enumeration
rows remain private. No runtime KASLR value was acquired or published.

The initial indexer stopped at embedded data in the two newly inspected PE
modules. A private derivative skips undecodable instruction slots to find
candidates; the relevant functions were then read directly from their PE bytes.
Its broad index is navigation evidence, not proof that every guessed function
boundary or string annotation is correct. Shifted immediates and branch
conditions were interpreted from the instructions, not the indexer's comments.

## Minimal change and validation

The only production source change is the fixed `TEXT` staging address in
[`build_loader.py`](../../workspace/public/src/mainline/s22plus_canary_h0/build_loader.py).
It now lies above the entire retained normal source-file envelope. The complete
new staging/BSS/stack interval fits retained RAM, excludes the candidate's
active reservations, and does not overlap kernel, DTB or initramfs destinations.
The former live-stub rejection remains necessary for other unsupported source
placements and still rejects without stores.

The entry assembly and copy implementations are unchanged. The exact retained
kernel, DTB, RAM PID1/initramfs, USB configuration, protocol, deadlines and
recovery design are unchanged. No cache instruction, idle setting, display
driver or reset/control path was added. The kernel was not rebuilt.

| Check | Result and scope |
| --- | --- |
| Actual ABL helper + old loader | All 64 external PRNG selector inputs enumerated; 1 entry, 63 guarded rejections; rejected cases performed zero stores. EFI selection and EL1/cache-off state are supplied assumptions, not observed ML001 state. |
| Actual successor entry guard | All 64 source placements reach the backward-copy instruction with exact source end, destination and length, and no earlier store. This check stops before the copy. |
| Representative full relocation | First, middle and last source placements complete the actual full file copy; destination bytes, surrounding canaries, byte counts and entry state checks pass. |
| Existing actual-loader corpus | 20 cases pass, including both copy directions, overlaps, invalid state/placement, complete execution to the kernel branch and malformed-DTB stopping. |
| Linked memcpy/memmove corpus | 1,051 cases pass with alignment, exact access bounds, tails, aliases and surrounding-byte invariants. |
| Actual-EL QEMU | EL1 and EL2 enter the new relocated body with exact copied bytes; EL3 rejects. GDB does not rewrite entry registers. |
| Artifact | Cross-linked ELF is static ARM64; Image header, complete runtime extent, embedded members and destination bounds pass. |
| Packaging | Two repacks are identical, retain the original-A outer envelope and have only `boot.img.lz4` in the AP archive. |

These tests do not prove actual g0q entry, cache coherence, Gunyah permissions,
USB behavior or automatic recovery. Old raw results and their pins were not
edited. The successful source and new artifact receipts are retained separately.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| uniLoader | 44,461,952 | `fb4bd5cb2aa93f78fb2affd9a9c026208cec88510119d40e7a556dfdc2b4669b` |
| boot.img | 100,663,296 | `8a4f374349ca96e5479da134a810f1d377041dd55cbb467225c2b7c7ed687df4` |
| AP.tar.md5 | 24,186,921 | `cef66a9c50c221c0d00a410685a6f97137a23aec28fb3e061c1ba78f6fca2b13` |

## Early display finding and observer decision

The exact firmware contains the selected AMB655AY01 panel definition. Its
active dimensions are **1080 × 2340**, despite a stale description mentioning
a different height. It enables DSI command-mode auto-refresh with a frame
divisor of two. DisplayDxe also contains a continuous-splash-dependent
ExitBoot path that can preserve display operation rather than deinitializing
the panel/clocks. This is stronger evidence for investigating an inherited
framebuffer than the previous reservation-only comparison.

It still does not measure the active runtime scanout, buffer format/stride,
memory attributes, successful programming or actual refresh after handoff.
The static panel configuration is not a ready physical observer. No framebuffer
write or display MMIO operation was added. A future display observer should use
the smallest bounded inherited-buffer path if those remaining conditions can
be established; a missing marker would still not prove that execution stopped.

The selected minimal runtime successor is therefore **staging relocation only**.
The newly reproduced compatibility fault gives this experiment a concrete
purpose without making full display bring-up a prerequisite. Existing NCM
remains the authenticated success criterion.

For a later host-observer addition, the concrete scope is:

- Start before candidate transfer under the existing operation owner; stop at
  the original observation deadline or owner cleanup, without renewing either.
- Retain ordered attachment/removal/interface metadata for the exact bound
  USB2 path, with monotonic capture times and producer/drop/error status.
  Do not collect another target's traffic or USB transfer payloads.
- Keep sampled sysfs identity and authenticated NCM acceptance unchanged.
  A transient attachment or descriptor error is diagnostic evidence only.
- Exercise transient attach/remove, interface creation, wrong/adjacent paths,
  malformed/truncated events, overflow and cancellation with the real parser
  and recorder before connecting it to the live owner.

This is a scoped integration specification, not an implemented or activated
event collector. It is not a new mandatory gate on the staging correction.

## Provenance, review and completion boundary

The loader consumes `prepare-4` and `init-final-2`. Some earlier discussion
checks used `prepare-3`; its DTB is byte-identical and its differences in the
resolved config are debug-information settings. The previously discussed
crypto/DISPCC/SCM/SMMU/idle values were explicitly rejoined to the actual
`prepare-4` input here. Neither artifact inherits the other's provenance.

Applicable past-failure checklist rows: **ABI** (actual ARM64 entry and copy),
**ARTIFACT** (firmware producer through header/loader/AP joins), **SEMANTIC**
(conditional static reproduction is not a measured failure attribution),
**DISPLAY** (configuration versus actual visible output), **HOST/ROUTE**
(event collection remains a specification), and **RETURN** (original physical
Download recovery remains separate and no new recovery is claimed).

This unit ends with a built, tested boot-only **H0 comparison successor** and
its required independent changed-loader review. The final review returned
`PASS_H0_SOURCE_BOUND_LOADER_ENTRY_AND_BOOT_PACKAGE` with no findings, bound to
15 critical sources and 63 artifact/raw-evidence receipts. It also reverified
49 immutable receipts from the predecessor review; no old evidence was replaced.
It reuses the retained canary
identity for controlled comparison and is not a newly admitted live candidate.
The current admission producer still binds the first candidate's evidence
paths; it was not repinned or bypassed. Fresh successor identity and the exact
new artifacts/review must be connected through the current owner before any
new finite attended run can be prepared. ML001 and its grant cannot replay.

Private evidence is under
`workspace/private/outputs/s22plus-mainline-entry-observer-h0-20261028-1/`,
including firmware/module pins, disassembly, source snapshots, both envelope
checks, new loader/test/package directories, and the independent review.

## External review follow-up, 2026-10-29

At the operator's request, Claude Opus 5.5 (`high`) and Gemini 4 Argon High
(`high`) each completed two supplied-evidence review rounds. They exchanged
first-round conclusions and received the actual admission consumer and one
additional execution result. Neither invoked tools. Both final reviews found
no actionable new defect in the fixed-staging change. These are advisory
reviews, not a replacement for the retained source-bound review or device
authority.

The first packet included `qualify()` but omitted its `image_binding()`
consumer. This caused Claude's initial claim that test/review receipts were
not joined to the actual loader/package. After reading that consumer, it
withdrew the claim: test loader hashes, package receipt hashes, key-derived
identity and reviewed receipt sizes/hashes are already checked. The fixed
relative evidence paths remain a documented next-candidate preparation issue,
not a demonstrated acceptance bypass.

Claude also withdrew its claim that the general live-stub-guard result string
was stale. The guard remains correct. Recording the source/staging margin may
be useful, but forcing disjointness would add an unnecessary condition to a
loader that already supports safe backward overlap. No new gate or firmware
constant duplication was added. Argon corrected its initial suggestion that
unchanged source/compiler flags alone establish reusable linked-copy evidence.

One narrow test suggestion was useful: the existing full-loader case started
at the staging address, while the three actual source placements stopped at
the relocated entry. A new private test uses the unchanged successor blob at
the maximum normal selector and executes the combined backward relocation
through the kernel branch. It passed in 35.514 seconds, checking BSS zeroing,
stack bounds, synchronization, kernel argument registers, exact kernel/initrd
destination bytes, and rewritten FDT properties/reservations/version. The
wrapper passed `py_compile`; its source, actual checker, loader/ELF and source
enumeration inputs are pinned. This supplements the original evidence without
changing its receipts. It proves emulated control flow to the kernel branch,
not Linux execution, physical cache behavior, Gunyah access or USB success.

The next bounded unit remains fresh canary identity/key and exact successor
artifact qualification through the existing owner. The current consumer still
requires matching loader-test, actual-EL and reviewed artifact receipts; old
results cannot simply be relabelled. Unchanged capability review and kernel
evidence remain reusable within their recorded scope. A fresh output layout
can satisfy the existing relative receipt names; an admission-producer code
change, if selected, needs its scoped review. Display and host USB event
diagnostics remain optional follow-ups.

No production code, candidate registration, activation, grant, device command
or transfer changed during this follow-up. A90, S20+ and unrelated dirty work
were untouched. Raw replies, prompts, the added test and results, model
identity checks and before/after usage accounting are private under
`workspace/private/outputs/s22plus-mainline-placement-external-review-20261029-1/`.
Claude's initial quota query returned HTTP 401 and is recorded as unavailable;
later snapshots and all four successful calls' token totals are retained.
