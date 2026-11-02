# S22+ LA002: loader LOGM write/read control

Status: **Qualified and independently reviewed; fixed preapproval D0 passed;
awaiting exact finite attended approval**.

After ML015 returned no V2 markers, the operator selected a positive-control
successor to the healthy LA001 loader-to-Android path. This control observes
the loader's write conditions and readback through its current FDT, then reads
the Samsung snapshot in that candidate Android before original-A restoration.
The final product remains mainline Linux and resident Debian.

## Selected change

The existing loader profile has one optional `logm_control` descriptor. It
keeps the byte-identical original-A kernel, inherited initrd, current ABL tree,
existing owner and one-shot normal return. After the final kernel/FDT copies,
one C function attempts a 128-byte frame in the first slot of the existing
256-byte LOGM span. Header, CPU and exact live-region guards precede access.
Header words are never written. The call reports skips, partial writes and
readback outcomes into a preallocated 128-byte final-FDT property.

The collector seals fixed FDT and last_kmsg captures between complete
candidate health proofs under the original 240-second window. Diagnostic
negatives remain separate from Android health. Acquisition failures preserve
the original stopped owner and A recovery; no new retry or control authority
is added. The namespace remains the existing loader family; LA002 identifies
this fresh candidate and report, not a new transport.

## Design review and proof limits

Two rounds of Claude and Argon discussion recommended this control. Their
initial causal interpretations were corrected: a current header skip cannot
explain old mainline zeros, readback mismatch does not identify a failed store,
and an absent snapshot frame does not prove overwrite. The proposed cache
clean operation was withdrawn because it changes the tested method and can
write back inherited dirty lines. The selected writer retains ordinary byte
stores and barriers. A separate independent design review checked the final
copy site, reservation/phandle link, FDT headroom and candidate capture scope.

The current FDT provides the observed boot's writer status; a static candidate
frame in the snapshot provides candidate occurrence. They do not prove a
shared attempt across an unseen earlier boot. A predicted snapshot offset is
not an acceptance gate. No reset-retention, mainline-boot, historical-cause or
automatic-recovery claim follows from this control.

## Qualification

The first build exposed missing constant macros in the loader's minimal
stdint header. Replacing them with explicit-width literals produced a working
build; the failed build and logs are retained. Independent review then caught
a family-namespace mismatch and acceptance of impossible EL/unread SCTLR
values. Both were corrected. Ambiguous or duplicate LOGM properties and
alternate phandle representations are also rejected before access.

The selected build-3 has a 1,004-instruction pre-store guard with no stack,
stores or calls. Its actual ARM64 qualification passes 113 loader cases,
1,051 aligned-copy cases, 44 local writer cases and four FDT-space cases.
The writer corpus covers all four header-word changes, byte mismatch,
interrupted prefix/body/commit stores, odd/cross-boundary indices, CPU states,
ambiguous FDT properties and guarded skips. Maximum input and maximum-plus-one
exercise admission; the actual allocator/packer succeeds with space and
rejects insufficient space without touching LOGM.

The full retained 4,448-node FDT remains in the actual guard corpus and in
actual EL1/EL2 QEMU handoff. The four Python-traced full copy/jump cases use a
separately pinned fixture retaining the actual memory banks, initrd, all
reserved-memory nodes and LOGM declarations. The full real-tree VM checks
the original kernel, immutable marker, all existing final-tree properties,
reservations and header fields, plus the entire 2 MiB LOGM slice. EL3 rejects
before stores. This division avoids repeating the large unrelated peripheral
tree in every instruction-traced writer case; it does not replace the real
tree or change device deadlines.

The first full-tree Unicorn run reached its instruction budget in libfdt.
A later maximum-size allocator fixture also exceeded its initial H0 budget.
Their raw failures are retained. Successful unchanged cases were revalidated
from their complete outputs and exact source bytes; only the incomplete
capacity cases and cheap copy corpus were rerun with the corrected H0 budget.
The selected result records old producer and current checker provenance.

All 44 saved actual-writer RAM cases match the unchanged extracted Samsung C
consumer and the existing snapshot model. The harness was also cross-compiled
to ARM64. A final reporting error on a hard-linked historical source was
repaired from the saved RAM and verified source; it did not repeat a producer
or device operation. This is host execution with memory shims, not physical
retention evidence.

The current observer, owner and connector tests pass 48 cases, including raw
failure preservation, wrong report/boot/USB rejection and diagnostic-negative
normal return. Two boot-v4/AP packages are identical. The current H0 artifact
checker validates the actual new package and retained LA001 artifact, without
capability or run authority, and rejects four malformed descriptor/declaration
variants. The absent-descriptor build has byte-identical
executable code and addresses to LA001; fresh marker data remains distinct.
The scoped raw-first source audit passes. Final independent source/artifact
review is `PASS_GO` with no unresolved findings. It checked the exact ELF,
generated declarations, real-FDT/whole-log EL evidence, all saved consumer
cases, current artifact checker, absent-variant code and focused host tests.
The new loader capability and backend V23 receipts are published; the stable
worker and its invariant policy are unchanged. The H0 task is prepared.

One fixed preapproval D0 invocation passed the complete seven-read rooted
original-A health bracket, raw producer checks and exact-task freshness.
No F1 owner or grant is open. Only the generated exact approval and actual
attendance with usable physical Download recovery remain before execution.

Applicable past-failure checklist rows are ABI (aligned accesses and C/jump
arguments), SEMANTIC (current FDT versus static frame evidence), IO/WIRE
(bounded shell-v2 raw producers), ARTIFACT (actual linked data and packaging),
ROUTE (optional descriptor through the existing family and observer), and
RETURN/AUDIT (original owner, immutable raw failure evidence and A health).
Native storage, display and other-target capabilities are outside this change.

Private evidence is retained under
`workspace/private/outputs/s22plus-loader-logm-control-h0-20261103-1/`, including
the advisory prompts/results, separate before/after quota and token accounting,
original producer source, builds, raw test logs and independent review records.
No new grant, candidate transfer or device control has occurred. The completed
D0 is readiness, not execution authority. A90 and S20+
are untouched; existing unrelated work remains separate.
