# S22+ ML003: reset-report provenance and next progress observer

Date: 2026-10-30 KST. Target: SM-S906N / g0q / S906NKSS7FYG8.
Status: **BOUNDED_H0_PROVENANCE_COMPLETE; CURRENT_RESET_CAUSE_UNPROVED;
FOLLOWUP_OBSERVER_DESIGNED_NOT_IMPLEMENTED**.

The retained exact FYG8 reporter maps OEM reason value **6** to
`TZBSP_ERR_FATAL_NOC_ERROR`. Its source is separate from the printed
`restart_reason` word. The retained TZ image contains a writer for that OEM
slot, using a runtime configuration table and a guarded caller. This identifies
the reporting mechanism, not a fresh ML003 fault, an offending address or the
component that caused the observed loop.

The UEFI text `restored from storage` is weaker than its wording suggests:
the actual caller does not check its storage-read return before preparing the
log header and selecting that text. Actual-instruction fixtures reproduce the
same label after a failed read, including an initially invalid header. The text
alone proves neither successful restoration nor repeated copies of a marker.

No new device read, control, transfer, candidate, grant, firmware execution on
hardware or storage effect occurred. ML003's consumed operation and its
`NO_PROOF / ANDROID_CLOSED_HEALTHY` terminal are unchanged. A90, S20+ and the
unrelated dirty work were untouched. This is diagnostic H0 analysis and a
prospective design, not a new lane, gate, capability activation or run review.

## Evidence reused and newly checked

The [ML003 run](S22PLUS_MAINLINE_ML003_RUN_2026-10-30.md) proves at-least-once
loader-handoff and early `primary_entry` occurrence. Its existing raw capture
has 2,097,136 bytes and SHA-256
`30ad798244e3147cc0609eef68124b54f54112dea8b8e966b2e91d9a104d7581`.
The preceding Claude/Argon discussion rehashed this capture and identified:

- Six intact adjacent loader/kernel pairs, separated by 128 bytes within each
  pair. Different pair offsets do not by themselves count boot attempts.
- Six `upload_cause` and six `TZ OEM_RESET_REASON` lines containing the NoC
  label. Nearby `restart_reason` text is `0x2e160a42`.
- Six warm-reset headers and seven restored-storage headers.
- Six NoC detail sections saying `tz log is encrypted or not parsed yet!`;
  XPU and SMMU detail sections contain the same availability message. This is
  not evidence that all three error classes occurred.

The current unit reopens the actual firmware consumers. It does not treat
model agreement, a string's presence in a binary or a function-name guess as
execution evidence. String/call indexes are navigation only; the conclusions
below follow selected instructions and their actual data references.

| Retained input | SHA-256 |
| --- | --- |
| Original FYG8 BL archive member, 114,319,472 bytes | `e5aeb59de4ed16c21111945900aeda4743b717361b0919084e9d284d08e4e0ba` |
| `XblRamdump.elf` | `0fc28798d2cfa24de2fcc370ffb0715ee73da81cf88b86727cfd71dd10cc5db6` |
| `uefi.elf` | `e026256bb4e6729b9652f8c8d67617321c0016dbecbac701d264f206385f11bd` |
| `SecEnvDxe` PE extracted from that UEFI image | `8e16fb88d0a7b016cccca33ae029a319c0f7ed276f6b4ffc943d0247d8a6b99c` |
| Retained FYG8 `tz.mbn` | `cab408c411728754222273a1298f1c31795cc54a7646b487a6569430e318f8f9` |

The original ZIP's BL member was verified before extracting the two selected
XBL images as inert data. The reporter is in plaintext `XblRamdump.elf`.
The UEFI reporter was recovered from one of the two bounded gzip volumes;
its PE digest also matches the previously retained SecEnvDxe identity. No
decryption, firmware modification or fresh device acquisition was used.

## Three separate reason paths

### General restart word

`collect_rr_data` calls the word reader with its clear argument set, saves the
returned value, and later prints it as `restart_reason`. The helper loads the
word and clears that same word when the low byte of its argument is nonzero.
It returns the original value. Six actual-instruction fixtures cover zero,
the captured `0x2e160a42`, and a distinct nonzero value, each with clear off/on.

This is a concrete read-and-clear consumer. It does not demonstrate a reset
reason generation identifier, explain the captured number, or prove that every
appearance of the printed line came from a fresh invocation. In particular,
`0x2e160a42` must not be used as the OEM enum or assumed to be a decoded NoC
cause simply because both strings occur in one log section.

### OEM reason and upload text

The same reporter independently loads the OEM word. Its bounds check admits
values through `0x82`; an out-of-range value takes the diagnostic fallback.
For the captured label, table index **6** points to the full NUL-terminated
`TZBSP_ERR_FATAL_NOC_ERROR` string. This direct table relationship is verified
from the retained bytes. A separate OEM getter leaves its slot unchanged;
four instruction fixtures cover zero, 6, the upper valid bound and the next
out-of-range value.

The `upload_cause` line prints a separate, previously populated string buffer.
The label is not independently generated by rereading the general restart word
at that print site. Two matching lines therefore are not two independent
measurements of the reset event.

Conditional implication: if this exact reporting path generated a fresh OEM
line with this label, its selected OEM table value was 6. The capture can also
contain retained text, so this implication does not by itself establish a
fresh value on the ML003 attempt or a measured reset executor.

### TZ-side writer

The retained TZ image has a writer for that same OEM slot. It first stores a
sentinel, obtains `/tz/oem` and `OEM_reset_reason_list`, and maps its incoming
code through the returned table. A matching row supplies the stored value;
for a nonempty returned table, the no-match path selects its final row.
Lookup failure can leave the sentinel.
The inspected caller sets a one-shot flag before passing its incoming code to
the writer.

This is a producer-to-consumer address join in retained firmware bytes. The
runtime property-table contents, the caller's actual code, its flag generation,
and complete boot/reset initialization of the OEM slot were not established.
The sentinel store belongs to this writer invocation; it is **not** a proved
clear on every boot. The direct-call census is navigation evidence, not proof
that no indirect caller or other writer exists.

These unresolved runtime inputs are the stopping boundary of this bounded
unit. It does not expand into all secure-firmware initialization, configuration
reconstruction or encrypted diagnostics. The current verdict remains
**reporter semantics established; event freshness and ML003 cause unproved**.

## What the restore label actually establishes

The normal SecEnvDxe path requests a fixed-size read into the same LOGM region
used by the marker. Its helper selects BlockIO read for mode 0 and write for
mode 1. The caller can subsequently issue the write mode when the in-memory
header is valid. This is static evidence of firmware storage handling, not a
new host or Linux storage operation in this task.

The crucial ordering is:

1. Request the read, without checking its return in this caller.
2. Inspect the in-memory header and optionally call the write mode.
3. Prepare the header: retain/increment a valid header, or initialize an invalid
   one with the valid magic and reset the payload.
4. Select `restored from storage` from that **post-preparation** magic.

All four actual-caller fixtures reach the restored label: read-success/failure
crossed with an initially valid/invalid header. Protocol and storage calls are
stubbed; the relevant branches and header-preparation instructions are the
actual PE bytes. Thus the counterexample does not rely on a rewritten model of
the text selection.

This proves the label cannot authenticate a successful restoration. It does
not prove that ML003's observed restorations failed. The static read path also
does not establish that distinct marker offsets were made by distinct kernel
entries, nor that copies actually duplicated those markers. Their original
at-least-once, no-same-boot/no-last-attempt interpretation is retained.

## Validation and provenance

**14 actual-instruction H0 cases passed**: six general-word read/clear cases,
four OEM-getter cases, and four restore-label cases. Flat-memory fixtures do
not model the device's MMU, caches, secure firmware state, reset persistence or
BlockIO implementation. Firmware code was emulated on the host, not executed
on the device. The check's first run used a 24-byte read for a 25-byte string;
the corrected 26-byte NUL-inclusive read verifies the full existing string
without changing any firmware or relaxing the expected value.

Python helpers passed `py_compile`. The private receipt binds the firmware
identities, exact code/table spans, source checker and all fixture results.
The prior discussion's Image/ELF/config joins are reused: eight early functions
match the actual ML003 Image, the 48-bit fallback is present, and BSS plus
initial page tables remain inside the already qualified runtime extent.
No kernel rebuild or repeat loader qualification was needed.

Past-failure applicability: ARTIFACT binds actual firmware bytes and table
pointers; ABI checks the actual load/store and argument behavior; SEMANTIC
separates reporting, text retention and fresh cause; WIRE keeps candidate
occurrence separate from boot counts; RETURN preserves original closure and
health. There is no new mandatory gate or policy change.

Private roots:

- `workspace/private/outputs/s22plus-mainline-ml003-reset-provenance-h0-20261030-1/`:
  extraction, selected disassemblies, navigation indexes, `audit.py` and
  `audit-result.json`.
- `workspace/private/outputs/s22plus-mainline-ml003-next-discussion-20261030-1/`:
  original raw-context inventory, Image joins, model responses and usage.

## Next bounded design: MMU transition and early C progress

The practical follow-up is a new two-site progress observer. It keeps the
RAM-only canary and original-A return objective. This section is a design
proposal only; no implementation, new artifact qualification or activation is
claimed.

| Proposed site | Positive claim if its new record is recovered | Still unproved |
| --- | --- | --- |
| `__primary_switch`, before `__enable_mmu` | Progress past initial idmap creation, EL setup and CPU setup | MMU enabling, kernel relocation and C entry |
| `setup_arch`, immediately after `early_ioremap_init`, before `setup_machine_fdt` | MMU, early mapping/relocation, `start_kernel` and initial fixmap progress | FDT scan, the rest of `setup_arch`, drivers, PID1 and USB |

The first site can reuse the bounded MMU-off leaf's approach while preserving
the computed SCTLR argument and startup registers. The actual little-endian
`INIT_SCTLR_EL1_MMU_OFF` does not set M/C/EE, but the new site still needs its
own emitted-code and actual-state qualification.

The second site requires a separately reviewed MMU-on writer. The actual build
enables `CONFIG_ARCH_USE_MEMREMAP_PROT` and `CONFIG_GENERIC_EARLY_IOREMAP`, so a
bounded explicit temporary mapping is available there. Existing `no-map` stays
in place. The header and selected slot can occupy different pages, and a
128-byte slot can cross a page boundary. Mapping size, attributes, possible
aliases, cache visibility, barriers, cleanup and failure/skip paths must be
qualified before selecting the actual writer. Default cacheable `early_memremap`
or an unchecked `phys_to_virt` is not an established solution.

A prospective new schema can keep two 128-byte slots and the complete candidate
identity/integrity fields, assigning them to these two later sites instead of
the old loader/entry sites. It must have distinct semantics and provenance;
existing V1 stages, artifacts and consumed results are not relabelled. The
exact schema and memory-attribute choice remain implementation decisions.

Implementation completion would require actual emitted producer/consumer
checks, mapping and boundary failures, positive-only decoding and the existing
changed-closure review. These are prospective conditions for the changed
capability, not a retrospective gate on ML003. A missing later record still
cannot locate a crash. Watchdog controls, UID changes, storage access and
display bring-up are outside this follow-up.
