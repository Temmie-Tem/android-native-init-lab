# S22+ P454: fixed journal recovery preparation after P453

Status: **H0 complete — READY_H0_PRELIVE_ONLY; no device grant**.
Only operator-owned `SM-S906N/g0q/S906NKSS7FYG8` is selected.

Subsequent [P454 execution](S22PLUS_JOURNAL_RECOVERY_P454_RUN_2026-10-23.md)
consumed the separately returned grant and closed healthy. The preparation
facts and unexecuted state described below refer to the H0 preparation stage.

The closed [P453 reader](S22PLUS_AUTOBOOT_EVIDENCE_P453_RUN_2026-10-23.md)
captured P452's authenticated early file but no runtime file in its checkpointed
home-block view. State 1, RECOVER 1, orphan 0 motivates this separate recovery
qualification; it does not establish all current writer-eligibility checks.
P452/P453 original raw evidence, sources, consumed actions and closures remain
unchanged.

P454 `v0.16.0-rc.3` is a fresh instance of the existing
[strict journal recovery](../operations/S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md).
Retain the pathless internal-JBD2 replayer, checker, partition-only RO handling,
bounded child settlement, normal/physical original-A return and the exact
`post-autoboot-p432-v1` comparison. No general repair, orphan cleanup, deletion,
wildcard history admission, installed execution or retry is added.

The selected comparison intentionally omits later runtime/early files,
including the P452 pair. Complete-root comparison is expected to remain
negative. Settled replay, read-only checker, restored RO/protected cleanup,
complete root admission and Android health remain separate claims. Do not
fabricate the absent runtime bytes or update history from an unknown file.

The bounded unit requires actual A/B packages and the original artifact
consumer, fresh representative ARM64 clean/replay/unadmitted-runtime cases,
relevant retained fault evidence, focused checks and independent review of the
current reachable source closure. Then prepare one offline journal-recovery
operation / 1800 seconds, frozen sources and an unexecuted ordinary-terminal
entry bound to the exact preceding P453 healthy closure. No connected read,
grant opening, image transfer or native_data write is part of this H0 task.

Current execution must freshly verify exact partition identity, primary and
journal checksums, feature/geometry/ring bounds, zero errors and orphan state.
Original A restores Android boot and health; it cannot undo partial native_data
writes. Uncertain execution never permits a replay. Any later P452 pair read
requires a separate fresh candidate and grant after this operation closes.

## Qualification

The actual physical A/B build is byte-identical. The original package qualifier
and `image_valid(..., artifact_bytes=True)` pass for the 33,843,241-byte boot-only
AP. Physical and virtual A/B helpers are statically linked AArch64 ELF files.
The selected comparison table/header and journal execution binding are identical
to P450. Of 169 runtime source keys, 168 are unchanged; the shared automatic-boot
profile has later features outside this selected old-history path.

Three fresh real ARM64 cases pass. Clean root skips the writer and leaves the
whole disk unchanged. Committed replay preserves revoked and uncommitted blocks.
An unadmitted runtime file produces `RECOVERY_NOT_PROVED` after settled replay
and checker success. All three preserve bytes outside native_data and restore
partition RO. These VM checks do not establish Samsung I/O or USB behavior.

Seven journal, one observation and six shared task tests pass, with changed
Python compilation. Unchanged retained fault evidence is reused only with its
original source, toolchain and raw-result bindings.

Independent capability review completed **PASS_GO / V3_REACHABLE_CAPABILITY**,
findings empty, against 140 host and 169 runtime sources. It verifies the
complete actual AP/builder, current VM raw projections, initramfs members and
disk boundaries, nine retained raw VM cases and the original negative-return
consumer. P450 and P454 helper differences are limited to the fresh run identity
and GNU build ID. Explicitly denied later history/script-channel branches were
not reached while generating the selected old-history headers/table.

## Concrete offline preparation

The original `prepare_offline` completed with command acquisition blocked.
It produced a `READY_H0_PRELIVE_ONLY` task for one attended journal-recovery
operation / 1800 seconds, with retained target/recovery bindings and frozen
140 host/169 runtime sources. No current connected health or writer eligibility
is claimed by this offline proposal. The original runner repeats its fresh
lane/host/Android and native admission checks at execution.

The ordinary-terminal entry is unexecuted. It checks the original user and
NoNewPrivs=0, unchanged task/capability/snapshots, P453's exact raw-rederived
healthy closure and the actual returned approval bound to task, entry and
predecessor. It then uses the original grant opener and attended CLI once.
No operator-approval record, grant, operation, attempt log or F1 owner exists.
The 1800-second clock starts only when the original grant opener succeeds.

The separate concrete preparation/entry review is
**PASS_READY_H0_AND_UNEXECUTED_ENTRY**, findings empty. The original task consumer,
all host/runtime snapshots, raw-rederived P453 closure and six AST-only initial
guard cases pass. The complete entry was not run. The core review and its exact
public binding remain unchanged. Execution still requires the actual returned
finite approval, physical attendance and usable Download/original-A recovery.

Private evidence:
`workspace/private/outputs/s22plus-journal-recovery-p454-h0-20261023-1/`.
A90, S20+ and the 46 preexisting unrelated change paths remain outside scope.
