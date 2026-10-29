# S22+ mainline early markers: Samsung retained-log feasibility

Status: **H0_FORMAT_COMPATIBLE_SMALL_WRITER_DESIGN_FEASIBLE**.

The existing FYG8 Samsung log format can expose a small direct RAM marker
without porting the Samsung logger to mainline. The retained source, historical
stock module, actual ML002 DTB and an extracted-source consumer agree on the
relevant layout and copy behavior. This completes the bounded compatibility
assessment selected after LA001. It does not implement an instrumented kernel,
qualify physical marker retention or arm another experiment.

Only S22+ SM-S906N/g0q/S906NKSS7FYG8 was analyzed. Device actions: **0**.
A90 and S20+ were untouched. Consumed runs, artifacts and journals were not
modified; the existing unrelated boot-journal work remains paused.

## Actual writer and reader path

The retained ABL FDT selects `samsung,kernel_log_buf`, strategy 3, within a
partial slice of the shared Samsung debug reservation. The slice is 2,097,152
bytes: a 16-byte little-endian header followed by 2,097,136 payload bytes.
The header contains `boot_cnt`, `magic`, `idx`, and `prev_idx`; the magic is
`LOGM`. This is firmware-shared diagnostic memory, not free or exclusively
owned RAM. The preserved P424 capture contains XBL log traffic as well as the
one previously authenticated native PRE marker.

The original Samsung driver performs these steps:

1. Map the reserved slice and check magic. Invalid magic resets `magic`, `idx`
   and `prev_idx`, while preserving `boot_cnt`; the subsequent snapshot is empty.
2. Allocate a separate buffer and copy the old ring into it. For `idx <= S`,
   where `S` is payload size, copy the prefix of length `idx`. For `idx > S`,
   rotate the whole ring at `idx % S`. Equality takes the prefix branch.
3. Expose that copy through `/proc/last_kmsg`, then append the current kernel's
   early messages and initialize the live logger.
4. Optionally compress the separate snapshot. The retained FDT selects zstd;
   opening the proc file restores the snapshot before its bytes are read.

The reserved RAM itself therefore does not need a compressed marker. Neither
`boot_cnt` nor `prev_idx` selects the snapshot or proves that it contains only
one boot. Normal Android log traffic after the snapshot does not change that
already copied snapshot. Firmware activity before it can still overwrite the
ring, reset its header or lose the underlying RAM contents.

Source identities are the existing snapshot model's unchanged FYG8 pins:
`sec_log_buf_main.c` SHA-256 `296f4fc175d958feb35b92c8736faf6361ade2e7c447d9a9af5a93f59bdb97b8`
and `sec_log_buf_last_kmsg.c` SHA-256 `ba9e0f9f0832cbf666e55b51804515fc8298203fd37958ccdfb6bfbbe3524443`.
The retained P424 stock module has SHA-256
`b4751eb8243a2bce4cd2f7b5f157f8429b295798dc310e23e861648906d24b61`.
Its ARM64 disassembly independently corroborates the index offset, payload
offset and prefix/rotation branches. This does not claim a fresh inspection
of the module currently loaded on the phone or complete source/binary equivalence.

## Small prospective design and its limits

The next H0 implementation can use two bounded stage records in one small
region, initially budgeted at **256 bytes total**. This size is a feasibility
fixture, not an adopted wire schema. Reuse the existing header-preserving
Carrier placement: with `c = idx % S` and record span `R`, choose `c-R` when
`c >= R`, otherwise `S-R`. With valid magic and `idx >= R`, the whole span is
visible to the unchanged reader if no intervening writer changes it. There is
no need to fill the entire ring or manufacture an index.

The proposed emission sites are:

- **Loader handoff:** the actual `load_kernel_and_jump` path after the kernel,
  rewritten DTB and initramfs copies, before the final kernel branch. Preserve
  FDT/register arguments and the existing barrier/branch sequence.
- **Kernel entry:** a bounded leaf in the actual `primary_entry` path before
  MMU activation, preserving boot arguments and startup registers. It would
  observe entry to that point, not `start_kernel`, PID 1 or USB readiness.

The retained stock reservation is not `no-map`; ML002's corresponding active,
non-reusable reservation **is `no-map`**. Consequently the old vendor-kernel
`phys_to_virt()` writer cannot be copied into ordinary mainline C and assumed
valid. A small early physical-access writer is plausible on the loader's
checked MMU/data-cache-off path. Its implementation still needs explicit
CurrentEL, SCTLR M/C/endian checks, bounded accesses and store-completion
barriers. `record_mmu_state`'s `x19 == 0` alone is not an independent check that
both M and C are clear. A later writer would instead need a deliberately
reviewed mapping; removing `no-map` is not part of this design.

The proposed writer preserves all four header words, skips recording if magic,
space or header stability is unsuitable, and never initializes the logger or
registers a live printk sink. A header bracket detects some interference but
does not establish a lock against firmware or prevent later overwrite.
Failure to record leaves progress unknown and should not stop the original
boot path. This confines the prospective extra memory effect to the small
declared diagnostic slice; the final code and effect still require review.

A fresh candidate-specific identifier, distinct stage fields, bounded length
and integrity check can reject stale foreign or torn records. Exact artifact
provenance must bind those fields and the two emitting code sites. A checksum
alone is not authentication. Since a boot loop can enter the same artifact
several times, two retained stage records would initially establish only
that the respective sites ran at least once during that candidate's attempts.
They cannot establish one shared boot, the last attempt, stage ordering across
resets, or why reset occurred without additional measured boot identity.
An absent, damaged or overwritten marker is **NO_PROOF**, not proof of
non-execution or proof that execution stopped at the preceding marker.

## Existing recovery and collection seam

[P424](S22PLUS_NATIVE_LOG_CALIBRATION_P424_RUN_2026-10-13.md) proves that one
authenticated native PRE marker survived its tested physical Download and
original-A return. Its full calibration pair and direct-mainline writing
remain unproved. That historical result is evidence that this route can carry
some bytes, not a guarantee for a new reset path or repeated boot loop.

The existing fixed reader already saves raw `/proc/last_kmsg` between two
same-returned-Android-boot health brackets. Its current task/profile allowlist
does **not** admit mainline. Reusing the command requires a reviewed mainline
owner/closure binding and a separate stage projection; passing a mainline task
as an old Debian/calibration task would be incorrect. No reader was invoked
or allowlist changed here. Recovery and final health remain independent from
whether any diagnostic marker survives.

## H0 checks and preserved evidence

The unchanged
[`s22plus_fyg8_retained_snapshot_model.py`](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_retained_snapshot_model.py)
was run against its exact source pins with a 256-byte synthetic marker.
The actual Samsung copy, append and invalid-header preparation function bodies
were also extracted unchanged into a private host harness; only kernel access
shims and their environment were supplied. **12 cases passed:** nine boundary
indices, invalid-magic reset, retention after 4,096 appended bytes, and loss
after an additional full-ring overwrite. The nine copy results equal the
existing model byte-for-byte. This is source-level host execution, not physical
or ARM64 execution of the module.

The same harness cross-compiled to an ARM64 relocatable object and `file`
confirmed its architecture. The stock source's GNU `void *` indexing emits a
warning in both harness builds; the source was kept unchanged. The first
extraction omitted return-type prefixes and failed compilation; that harness
failure and the corrected extraction are preserved. No firmware build was
needed for this assessment.

The exact retained ABL FDT and ML002 DTB were rechecked for the log slice,
backing reservation, zstd selection and active no-map coverage. P424 raw/live/
result file hashes were rechecked against its unchanged diagnosis receipt.
No missing current-device health evidence was replaced by those old records.

Private evidence root:
`workspace/private/outputs/s22plus-mainline-retained-log-feasibility-h0-20261029-1/`.
It contains `check.py`, pinned inputs, `snapshot-model.json`,
`actual-c-consumer.json`, `dt-ownership.json`, retained module disassembly,
compile commands/logs, `historical-retention-join.json` and `result.json`.

Past-failure checklist: ABI and ARTIFACT were checked against the actual header,
copy branches, source pins and DTB; SEMANTIC and WIRE retain positive-only stage
claims and unknown missing evidence; RETURN keeps P424's narrow physical proof
separate from the proposed observer. No live collector, protocol, authority,
health condition or gate changed. Remaining implementation qualification is
the actual two-site writer/decoder, final emitted artifacts and the mainline
collection seam, followed by the existing independent review and attended
finite-authority process before any new physical candidate.
