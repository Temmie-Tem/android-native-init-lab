# S22+ FYG8 uniLoader-to-Android control V1

Status: **REVIEW_GATED_CAPABILITY**

This ordinary attended boot-only F1 control uses the existing V3 Session,
target lease, consumed-content registry, measured Odin transport and exact
original-A recovery. It is limited to the operator-owned
`SM-S906N/g0q/S906NKSS7FYG8`. Its separate `loader-android-v1` profile and
`loader-android` operation are a comparison for the mainline project, not a
mainline RAM PID1 result, native admission or installed-Debian experiment.

## Candidate and qualification

The candidate replaces only the original-A boot image's kernel member with
the qualified loader. The loader embeds the byte-identical raw FYG8 kernel
extracted from that exact original A. The original outer ramdisk, signature
and AVB data, vendor_boot, DTBO and Android installation retain their identity.
Retaining signature bytes does not authenticate the modified boot payload.

The loader preserves the actual current ABL FDT argument before relocation.
Before any destination store, its bounded stackless guard validates that FDT,
the complete inherited initrd span (also disjoint from the loader source), fixed reservations and exact retained RAM
banks against the entire loader staging/BSS/stack, kernel runtime and FDT
destination. Its current compiled code and source-relative references must
pass the instruction checks. Unsupported entry state, source alignment or
input shape stops before stores; no speculative write follows rejection.

The full incoming tree is cloned, with one fresh candidate-bound
`/chosen/codex,uniloader-android-v1` marker added. Either optional diagnostic
below adds its one fixed report property. A preexisting selected marker or
report is rejected. Existing properties, memory reservations, initrd/bootconfig span,
boot arguments, version and boot CPU are preserved. The inherited initrd is
neither rewritten nor copied. The exact embedded vendor kernel is copied and
entered through the reviewed loader synchronization/jump path. No new
watchdog, shutdown, SCM, display, storage or network controller operation is
added by the loader. Normal existing Android runtime behavior is retained;
this profile adds no native_data reader, mount, replay, repair or data writer.

Qualification binds the actual loader, kernel, boot/AP, marker and current
checker evidence. It exercises the real ARM64 guard and complete loader,
including malformed inputs, overlaps rejected before stores, current-x0
preservation, unchanged initrd and tree properties, actual exception levels
and deterministic boot-only packaging. These are H0 evidence, not physical
boot, cache coherence or automatic recovery. The independently reviewed
capability closure includes the reachable observer/owner/return machinery;
artifact provenance and current host-source provenance remain separate.

### Optional LOGM write/read control

Only an image with the schema-exact `s22plus-loader-logm-control-v1`
`logm_control` descriptor and complete actual-code/actual-EL qualification may
select this diagnostic. The absent-descriptor variant retains its original
behavior. The family namespace/version remain unchanged; the fresh marker,
run identity, descriptor and exact artifact distinguish a candidate. Earlier
approvals and reviews do not authorize the changed capability.

After all kernel and FDT copies, immediately before the existing synchronized
kernel jump, one ordinary C call may inspect the fixed Samsung log slice at
`0x800200000`, size `0x200000`. The four aligned little-endian header words
remain unchanged. The entry guard keeps the whole slice inside the retained
RAM banks and disjoint from the incoming FDT, loader source, inherited initrd,
staging/stack, kernel and final FDT. It remains separate from the three ordinary
loader destinations; it is not treated as unreserved RAM.

Before any LOGM access, the call requires EL1/EL2, little-endian data, MMU and
data cache off, and the exact active live-FDT `samsung,kernel_log_buf` node,
partial slice, strategy 3, zstd snapshot selection and its unique phandle link
to the retained non-reusable, mapped Samsung log reservation. Ambiguous node
identity, changed region or unsuitable CPU state skips all LOGM access and
records the diagnostic outcome. It does not change mappings, cache controls,
watchdogs, peripheral registers, storage or the logger.

Valid magic and `idx >= 256` admit one 128-byte slot in the first half of the
existing 256-byte span. With `S = 0x200000 - 16` and `c = idx % S`, the span
starts at `c - 256` when `c >= 256`, otherwise at `S - 256`. The writer zeros
the eight-byte commit prefix, writes the remaining 120 bytes, rechecks all
four header words, and commits the eight-byte prefix only if they match.
Byte stores and completion barriers bound the total to 136 payload stores;
no second slot or header is written. A header mismatch after body stores
records an incomplete write, not a no-write skip. A committed frame gets one
128-byte readback and one final four-word header sample. No retry, header
initialization or cache-clean operation is added.

Before any LOGM write, tree construction allocates and packs exactly one
128-byte `/chosen/codex,uniloader-logm-v1` report. This variant reserves 512
bytes of input-tree headroom; the absent variant retains 256. After the final
FDT copy the writer resolves that property in the final tree and updates only
its existing bytes. No allocation or property relocation follows LOGM stores.
The fixed big-endian report binds the fresh candidate, observed EL/SCTLR,
final reason, valid/attempt flags, slot offset, readback mismatch count and
three numeric header samples. Missing or unfinalized reports cannot be
interpreted as evidence that no write occurred. The LOGM frame uses its own
candidate-bound HMAC magic/domain; it is static across attempts of that image.

For this descriptor, observation first obtains the existing complete candidate
Android proof. It then checks shell-v2, reads the fixed FDT report once (128-byte
maximum) and `/proc/last_kmsg` once (4 MiB maximum), and obtains another complete
candidate proof. These are fixed pinned-ADB `shell -T` privileged reads; raw
stdout/stderr and producer outcome are sealed before interpretation. Each data
read has at most 30 seconds and remains inside the original 240-second launch
window and grant. The complete proofs must share candidate boot identity and
USB generation across collection. The ordinary fresh pre-Download proof is
still required. No post-closure reader, general shell or read retry is adopted.

Structurally valid guard skips, header drift, readback mismatch and absent
frames are diagnostic outcomes and permit the unchanged normal return after
its current proof. Failed, partial, oversize or malformed acquisition stops
through the existing owner; original-A recovery remains independent of these
files. Diagnostics never replace or weaken either Android health bracket.

Qualification exercises the actual compiled writer, alignment and ABI, exact
store/read extents, guard negatives, all header-word changes, interrupted
commit/readback and the fixed Samsung snapshot consumer. Actual EL fixtures
cover full handoff and preservation of the final FDT and original kernel.
These fixtures do not prove physical cache coherence or reset retention.
Generated candidate data retains its original producer provenance; current
checkers and independent artifact review must join the actual frame, seed,
selection/enum declarations, ELF, boot/AP and raw qualification results.

The current FDT reports the observed boot's loader outcome. An exact frame
anywhere in its acquired snapshot proves candidate occurrence. The static
frame alone does not join that occurrence to the same attempt, exclude earlier
unseen boots, prove lack of intervening writes, or explain a missing frame.
Matching readback and a snapshot frame are reported as separate observations;
neither establishes mainline execution, historical failure cause, reset/
Download retention or automatic recovery. Original-A return and health retain
their independent requirements.

### Optional mainline prefix live witness

Only the schema-exact `s22plus-loader-mainline-prefix-v1` `prefix_control`
descriptor selects this variant. It is mutually exclusive with `logm_control`.
The loader embeds both the exact original-A vendor Image and one fresh full
mainline Image with the fixed returning `primary_entry` below. It uses a single
payload destination sequentially: mainline copy and bounded prefix entry,
return to resident loader code, exact vendor copy over the same destination,
and the existing synchronized vendor handoff. This is an entry-prefix witness,
not a mainline boot, RAM PID1, USB or installed-Debian experiment.

Before any store, the existing placement guard covers the entire enlarged
loader file/runtime, live FDT, inherited initrd and the union of both kernel
runtime intervals. The selected loader staging starts at `0xaa000000`; other
variants retain their original staging. Exact linked extents must fit retained
RAM and avoid every fixed reservation and protected input. The live source's
executing stub cannot be overwritten. Unsafe geometry parks without a fallback
boot attempt. The unchanged original ramdisk and both Images must fit the
original 96 MiB boot-v4 envelope and deterministic boot-only AP.

One fresh 256-byte `/chosen/codex,uniloader-prefix-v1` report is allocated and
packed before final FDT placement. This variant reserves 768 bytes of input
headroom. No property allocation or relocation follows diagnostic access.
Before any LOGM access or prefix entry, the same exact live-FDT LOGM layout
checks as the preceding control must pass, with EL1/EL2, little-endian data,
MMU, data cache and instruction cache off. An unsuitable sampled CPU state or
live logger layout records its explicit skip and continues to the exact vendor
Image without either marker writer or mainline entry.

For eligible state/layout, the loader calls the unchanged V1 loader-handoff
writer once, then enters the actual mainline Image header. Its fixed
`primary_entry` saves the return address in x18, calls the unchanged V1
kernel-entry writer once and returns to the resident loader before
`record_mmu_state` or `preserve_boot_args`. Only the existing two distinct
128-byte V1 slots within their fixed 256-byte LOGM span are writable; the
four header words are never changed. Each writer's existing magic/index,
header-recheck and eight-byte commit-prefix rules remain intact. The total
maximum is 272 payload byte stores, with no retry or header initialization.

The prefix returns its actual entry PC, CurrentEL, SCTLR and fixed cookie.
The resident caller preserves its normal callee-saved registers, SP and LR,
requires the exact PC/cookie and unchanged eligible CPU sample, and parks on a
bad return. The prefix performs no MMU, cache-control, storage, peripheral,
watchdog, SCM or reset mutation. The loader retains the existing synchronization
sequence before each Image branch. There is no general kernel-context restore.
Both Image calls receive the final live vendor FDT and x1–x3 zero; the prefix
does not parse that tree. This differs from the historical mainline-DTB path.

The report samples all four LOGM header words before and after each writer call.
When an after-call sample has valid magic/index, it derives that sample's slot
and compares exactly 128 bytes with the corresponding candidate frame. This
is a post-call byte observation, not the writer's returned outcome: V1 returns
no status. Header drift may make that derived slot different from the actual
write slot. A matching static frame may predate the current attempt. Neither
external header samples nor readback prove current-attempt stores, commits,
absence of intervening writes, reset retention or past failure causes.

The host obtains the existing complete candidate Android proof, checks
shell-v2, reads exactly this fixed report once with a 256-byte maximum and
30-second bound, then obtains another complete same-boot/USB-generation proof.
All reads remain within the original 240-second window and grant, with raw
stdout/stderr and producer outcomes sealed first. This variant adds no
last_kmsg read, post-closure reader, general shell or retry. A valid skip or
readback mismatch remains diagnostic and permits the unchanged normal return;
failed, partial, oversized or malformed acquisition stops the original owner.
Prefix-return proof and loader/vendor-Android proof are separate terminal facts.

Qualification binds the actual full prefix Image, its exact source recipe,
both unchanged V1 writers, generated declarations, enlarged loader/ELF and
boot/AP. Actual instruction tests and actual EL1/EL2 fixtures must execute
sequential full copies, the Image-header/prefix/return path and final exact
vendor handoff, preserving existing FDT/initrd semantics. Negative tests cover
guarded ranges, malformed/stale FDT, CPU/layout skips, header/index boundaries
and drift, interrupted reports, bad returns and ABI sentinels. Synthetic
fixtures do not prove physical coherence or a historical failure mechanism.
One current independent review and fresh exact candidate qualification are
required before the existing finite attended approval path. Failure recovery,
the original one-shot A, terminal health and no replay remain unchanged.

## Finite entry and observation

The target adopts the identical named
[mainline preapproval D0 profile](S22PLUS_MAINLINE_RAM_V1.md) and its existing
`s22plus_mainline_task_v1.py ready` entry for this exact comparison task.
Schema-specific validation selects the loader profile; the fixed original-A
identity/root/partition-digest transcript, no-owner/no-grant exclusion,
durable evidence and 300-second same-host freshness rule are unchanged.
This foreground read needs no separate attendance or per-read approval.
It does not execute the candidate observer, open a grant or change boot mode.

One exact returned approval and actual physical attendance bind one operation
and **1800 BOOTTIME seconds**, including suspend, on the same host boot. The
task binds the exact target/lane, source review, candidate and original A,
demonstrated usable physical Download recovery and private durable journal.
The ordinary normal graph is:

`fresh original-A health -> Download -> N once -> candidate Android proof -> fresh same-boot proof -> Download -> A once -> original-A health`

Candidate observation ends at its original transfer-launch time plus **240
seconds**, or the original grant deadline if earlier. Bounded ADB readiness
uses the existing bounded inventory reader and fixed `sys.boot_completed=1`
and `init.svc.bootanim=stopped` readiness before the proof bracket. Readiness
stays within the same original window and is not itself health. One complete
same-boot bracket then requires numeric root, normal FYG8 Android properties,
the exact candidate boot digest, original supporting partition digests, exact
vendor kernel release and exact loader-created marker digest. Every command's
bounded raw output is sealed before interpretation. A boot digest or screen
alone is not proof that uniLoader executed.

Immediately before the candidate's normal Download command, a new complete
fixed proof bracket must match the already observed candidate boot ID and
marker within that same original observation window. The unique Download
intent binds this proof and its own measured USB generation/departure window.
USB-generation snapshots bracket the fixed proof; the final dispatch snapshot
must still match that bracket, so a reattachment cannot reuse stale health.
The subsequent A arrival deadline belongs to that return intent, not initial
Android entry. No general candidate shell or arbitrary command is exposed.

## Stops, recovery and proof limits

Absent, failed, partial or changed candidate evidence stops research. A failed
or uncertain Download command never repeats. The stopped owner retains only
attended physical Download and the original one-shot A transfer/final health,
under the existing durable Session recovery rules. Expiry cannot renew N or
candidate control. A completed A with missing health permits only existing
health continuation; an uncertain A cannot be transferred again. Recovery
does not depend on candidate files, a readable marker or successful candidate
boot. No automatic failure recovery is claimed.

The normal return completes inside the Session. This profile does not inherit
the mainline physical-return continuation. Connector recovery requires the
original stopped owner. If a host interruption prevented its stop record, the
connector may reconcile that stop in H0 under the target lease, only for this
exact loader task: require the original same-host dispatch's immutable
`PROCESS_EXITED` result and matching non-live process identity, task, entry,
approval, grant, consumption and F1 owner; require a durable effect basis and
no terminal. A must have no intent or its unique intent must have raw-proved
completion. Append one current-time `stopped` record citing the settled
launcher result/spawn and preceding journal tail. This records the observed
interruption; it neither invents historical success nor backdates the stop.
The existing stopped-owner recovery then applies. Missing or uncertain
launcher results, whole-cgroup loss without settlement, uncertain A, or a
changed host boot do not qualify for this reconciliation.

Reporting failure after proven effects is repaired from raw evidence and never
causes replay. Historical H0 rederivation joins the original grant/readiness
host epoch; a later host boot does not erase complete raw evidence. All live
effects, including original-owner recovery, still require the current grant's
host epoch and cannot be revived by that historical rederivation.

PASS requires both current-boot loader/Android evidence and exact original-A
return/health. Missing loader proof can close NO_PROOF only after that return.
Preserve independent claims for loader entry/handoff, normal Download return,
original-A restoration/health and automatic recovery (unproved). A successful
control qualifies only the shared loader stages and selected vendor path.
It does not prove ML002's replaced-DTB path, mainline boot or a reset cause.
Failure alone cannot identify the failing component.

Keep the existing append-only journal, bounded private raw records, structured
terminal and canonical F1 timeline. This new capability receives one concise
report. No consumed candidate, approval, journal, historical review or other
target is changed. Changed hazard-relevant inputs require independent review;
routine candidate data uses fresh qualification within the existing rules.
