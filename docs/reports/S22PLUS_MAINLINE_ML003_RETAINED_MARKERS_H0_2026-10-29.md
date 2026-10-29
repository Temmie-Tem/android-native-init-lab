# S22+ ML003: two early retained markers prepared in H0

Status: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.

ML003 adds small positive progress records at uniLoader's final kernel handoff
site and mainline's `primary_entry`, while keeping the existing RAM PID1/USB2
experiment and original-A return. It follows the
[feasibility assessment](S22PLUS_MAINLINE_RETAINED_LOG_FEASIBILITY_H0_2026-10-29.md).
No physical ML003 experiment, grant or candidate consumption has occurred.
Only S22+ SM-S906N/g0q/S906NKSS7FYG8 is selected; A90 and S20+ are untouched.

Independent source/artifact review is **PASS_GO**, with no unresolved findings.
The exact image and task reopened successfully through the production admission
functions. The unchanged ordinary-terminal worker selected reviewed backend
v12 and completed the named preapproval D0. Its durable readiness journal and
complete raw health were rederived with the existing 300-second freshness
check; process exit alone was not accepted as readiness.

The fresh task has no operator approval, grant, operation directory or consumed
candidate claim. Device controls and partition transfers are **0**. Readiness
is a point-in-time observation and must still meet the existing freshness and
effect-time checks when an attended experiment is separately authorized.

| Preparation receipt | SHA-256 |
| --- | --- |
| Independent artifact review | `44177df43bd9e74858aef7c95df7b2678d90cb24931fe18ae07a951e1ff8bed7` |
| Mainline capability review | `fe4c92deee6db198dd83b7fa9c59471824af58be3649fb2a91723a03bfcfec92` |
| Backend v12 review | `f7f7a14da4e596c08c220902426fcac244ccd42b7967c7d01f7aeebcad9c987e` |
| New task | `3d8ce6e71df218b2f5b33cf3dda2ebffe69456ccb8437833fa7d65670d7cffe7` |
| Preapproval readiness | `b4e1caedd91049c7e1c0150596f64ed923554c4570f60a4da3c6dda323af617a` |
| Pre-experiment summary | `cac05f40a82fab01819fce1f344c3316f9053a4cb449e468f7ae58dec60ff1fe` |

## Implemented behavior

One shared assembly template emits two independently bound 128-byte frames.
Each site validates its actual exception level, MMU/data-cache/endian state
before accessing the fixed Samsung diagnostic slice. It preserves startup
arguments, stack and non-scratch registers, leaves the 16-byte log header
unchanged, and writes only its own slot through byte accesses. Invalid
conditions skip the recorder. The commit prefix is cleared first and restored
only after the body, barriers and a four-word header stability check.

The loader site follows the real kernel/DTB/initramfs copies and precedes the
existing synchronization and `br x4`. Its record proves that pre-branch point,
not execution of the subsequent branch. The kernel site precedes
`record_mmu_state` in the actual `primary_entry`. Its record does not prove
`start_kernel`, PID 1, USB or continued operation. Neither site changes a
watchdog, storage, mapping, interrupt control, firmware partition or logger.

Each static frame contains the fresh candidate identity, its distinct stage,
fixed format/length and a keyed integrity tag. The tag binds the generated
artifact; it is not a fresh runtime challenge. Decoding reports only positive
at-least-once occurrence during this candidate's attempts. A boot loop may
produce multiple records or move the firmware's ring index. The decoder makes
no same-boot-pair, last-attempt, reset-cause or missing-marker inference.

The optional image qualification joins both actual linked sites, generated
frames, kernel provenance, instruction tests and actual-EL fixtures to the
exact independently reviewed package. Partial marker source publication
cannot silently become an ordinary unmarked build. Prior artifacts and
reviews retain their original identities.

The new fixed mainline collector is separate from the older Debian collector.
It rederives the closed mainline N/A owner, original consumption, immutable
journal, raw final-A health and changed Android boot before collecting. One
bounded `last_kmsg` read is bracketed by health on that same returned boot.
The command/limits and fresh-read behavior are defined in the
[mainline policy](../operations/S22PLUS_MAINLINE_RAM_V1.md). Raw failure bytes
remain preserved. Offline projection neither creates journals nor runs I/O.
The original USB/PID1 terminal is not rewritten by diagnostic evidence.

Marker files and post-closure collection are excluded from original-A recovery
prerequisites. Historical mainline observation now joins its saved host epoch
to its original grant, permitting offline rederivation after a host reboot;
live grant/owner execution still rejects a different host boot.

## Validation and provenance

The original source tree was copied into a fresh private build tree without
mutable hardlinks to consumed artifacts. **94,874 source entries** were compared
before the one `head.S` instrumentation change. The config and g0q DTB are
unchanged; the physical initramfs has a fresh generated identity/key. The actual
kernel, loader, static ARM64 init and boot-only package are newly bound.

| Check | Result |
| --- | --- |
| Actual linked loader/kernel marker instructions | 342 cases passed, including all 135 incomplete store cuts at each site, index boundaries, alignment residues, rejected state and header interference |
| Actual QEMU exception levels | Six marker cases: both sites at EL1/EL2, and no writes at EL3 |
| Actual complete loader | 20 cases and 1,051 direct copy cases passed; full-copy case checks exact marker slot and unchanged header/outside bytes |
| Loader entry at actual exception levels | EL1/EL2 entry and EL3 refusal passed |
| Actual modified kernel with VM-specific PID1 | Authenticated observer passed; physical g0q behavior remains unproved |
| Two independent boot/AP packages | Byte-identical, one `boot.img.lz4`, retained original-A outer envelope |
| Focused source suite | 72 tests passed; subsequent collector suite has 12 passing cases, including normal/recovered closed-owner joins and missing-journal refusal |
| Ordinary-terminal connector | 78 focused tests passed |
| Optional-codec recovery regression | 39 focused tests passed, including missing/broken codec during a complete-USB normal-proof probe, original-A recovery and terminal fallback |

The instruction fixtures distinguish injected guard values from actual QEMU
exception levels. They prove neither physical cache/firmware behavior nor
retention through a real reset and Download return. The complete-kernel VM uses
an explicit VM PID1 and virtual networking, not the physical USB proof.

The initial full VM had no RAM backing at the fixed high diagnostic address
and did not reach its observer. A larger anonymous allocation was rejected by
the host. A sparse file-backed fixture supplied the address and the same kernel
then passed; no candidate change was needed for those fixture failures. The
temporary guest backing is removed after process settlement, while inputs,
commands, serial output and results are retained.

Two host checker issues were repaired with original failure evidence retained:
the linked loader's existing BTI landing instruction precedes the marker call,
and a marker expected-byte variable initially shadowed a boolean in JSON output.
These were H0 qualification failures and caused no device effect. The source
publication guard was strengthened during the kernel build; the originally
executed producer sources are retained, and the unchanged result was checked
with the corrected complete-source validator instead of rebuilding it.

Independent review also found that a missing or syntactically broken optional
marker codec could raise an import exception outside the existing recovery
fallback. Candidate marker validation now checks its current source review
before importing the codec and normalizes those two import failures into a
candidate-validation error. The existing A owner/transfer rules are unchanged;
the regression explicitly reaches the failing import during the normal-proof
probe before demonstrating the original one-shot A path.

Private evidence root:
`workspace/private/outputs/s22plus-mainline-ml003-h0-20261029-1/`.
Key records are `review-inputs.json`, `prepare-1/`, `init-1/result.json`,
`loader-1/result.json`, `qualification-4/result.json`, `entry-vm-2/result.json`,
`marker-qualification.json`, `marker-tests-2/result.json`,
`marker-entry-vm-2/result.json`, `vm-3/`, `package-1/result.json`,
`focused-tests-1.log`, `collector-tests-4.log`, `connector-tests-1.log` and
`recovery-and-marker-tests-2.log`.
The final review and its 63-file source snapshot are in `review/`; `image-1/`,
`task-1/`, `connector-preparation.json` and `preexperiment-ready.json` preserve
the qualified preparation and named D0 result. Old reviews and the persistent
worker/invariant policy remain byte-identical.

Checklist applicability: ABI/ARTIFACT bind actual emitted code, byte alignment,
state checks and fresh package identity; WIRE/SEMANTIC preserve torn-record and
positive-only meanings; ROUTE/PERSIST exercise real raw/health consumers and
both closed-owner shapes; RETURN keeps observation separate from one-shot A
recovery. The paused Debian boot-journal work and all consumed device records
remain unchanged. Physical reset cause and mainline progress on g0q are still
unproved.
