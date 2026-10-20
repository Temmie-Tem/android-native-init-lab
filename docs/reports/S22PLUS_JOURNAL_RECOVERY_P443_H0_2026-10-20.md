# S22+ P443: strict journal recovery after P441

Status: **PASS_GO / READY_CONNECTED_FIXED_D0; no grant or replay effect**.
Only `SM-S906N/g0q/S906NKSS7FYG8` is selected.

Prepare a fresh instance of the existing
[fixed journal recovery](../operations/S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md)
after the closed P441 writer and
[P442 reader](S22PLUS_AUTOBOOT_EVIDENCE_P442_RUN_2026-10-20.md).
P442 saw state 1, RECOVER 1, orphan 0, recovered the complete authenticated
early file and found no runtime file in the dirty home-block view. These
observations select new H0 preparation; they do not renew consumed P439.

Retain the existing strict replayer, checker, `post-autoboot-p432-v1` history
selection, finite owner, partition RO restoration and original-A recovery.
The new candidate changes only its fresh identity. Its complete comparison
does not admit the later P432 runtime, P437 pair or P441 pair. Known later
files therefore remain expected comparison failures; newly exposed runtime
bytes require separate retrieval and qualification. No deletion, wildcard
admission, extra repair or replay retry is selected.

Completion requires actual A/B package/consumer qualification, representative
ARM64 cases, unchanged-evidence reuse review, focused checks, independent
current source-bound PASS_GO and a concrete attended one-operation/1800-second
proposal. Execution still requires that proposal's exact returned grant,
current target/health and usable physical Download recovery.

The operation may reproduce already committed journal changes on native_data.
Original A restores Android boot and health; it cannot undo those data writes.
Writer settlement, checker outcome, exact root comparison and Android return
remain separate claims. This capability does not run installed Debian.

Private H0 evidence:
`workspace/private/outputs/s22plus-journal-recovery-p443-h0-20261020-1/`.
P441, P442 and all earlier consumed actions retain their original evidence.
A90 and S20+ remain outside this work.

## Qualification and concrete readiness

The fresh `p443` / `v0.13.0-rc.0` physical and virtual A/B helpers differ from
P439 only in their run identity and GNU build ID. Strict replayer, checker,
generated root table and the selected two historical rows are identical.
The full boot-only A/B packages are byte-identical; independent archive,
Image/CPIO, source-closure and current image-consumer audits pass.

Three fresh ARM64 cases pass: clean-root writer skip, committed replay with
revoked/uncommitted blocks preserved, and a runtime file outside the selected
table. The last preserves `RECOVERY_NOT_PROVED` after settled replay/checker
completion and partition RO restoration. Nine retained failure/boundary cases
rederive from their original raw/CPIO/disk evidence through the current decoder.
Actual owner mutations reject missing settlement, RO or cleanup, truncated
proof, wrong binding and duplicate intent. Fourteen focused journal/task tests
and touched Python compilation pass.

Independent review is **PASS_GO / V3_REACHABLE_CAPABILITY**, findings empty,
binding 139 host and 169 actual builder sources. Changed declarations and
higher-precedence interactions were reviewed against the unchanged selected
journal path. Historical reviews remain intact. The new capability and exact
execution sources are frozen privately.

Fresh foreground D0 preparation completed 17 bounded captures. Rooted
original-A health brackets match on the same Android boot; exact partition
hashes, shell-v2, full GPT and Android32 capacity pass. Host lane, holders,
readable exact rollback, retained recovery binding and absence of an F1 owner
pass. The raw-derived preparation and actual task/proposal reopen successfully.

No P443 grant, mode change, image transfer, native_data read or replay occurred.
The concrete proposal is one attended `journal-recovery` operation within
1800 original BOOTTIME seconds. The existing lane still requires its exact
returned grant and usable attended Download recovery before the single N.
The consumed P442 grant cannot authorize this separate persistent write.
