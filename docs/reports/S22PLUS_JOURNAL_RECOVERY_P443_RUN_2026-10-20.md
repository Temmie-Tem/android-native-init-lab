# S22+ P443: strict replay completed; complete-root comparison remains negative

Status: **RECOVERY_NOT_PROVED / ANDROID_CLOSED_HEALTHY**.
Only `SM-S906N/g0q/S906NKSS7FYG8` was selected.

The operator returned the exact attended one-operation/1800-second grant for
the [qualified P443 candidate](S22PLUS_JOURNAL_RECOVERY_P443_H0_2026-10-20.md).
One fresh N, one strict journal operation and one original-A transfer are
consumed. The fixed operation completed and returned to healthy original
Android32; no F1 owner remains.

## Replay, checker and root comparison

Initial native_data was state 1, RECOVER 1, orphan 0. The strict writer completed
**24 writes / 95,232 bytes**, including its successful finalization, with no
reported I/O error. Its child was reaped and settled. Partition RO was restored;
the separate read-only checker completed successfully. The post-replay
superblock was clean: state 1, RECOVER 0, orphan 0.

Protected inspection matched all **8,971** expected entries without reported
metadata, content or missing-entry findings. The complete tree contained
**8,981** entries against **8,976** admitted by this comparison's archive,
fixed structural and bounded-extra accounting. Five entries remain outside
that accounting, so the actual verdict stays `RECOVERY_NOT_PROVED`.

The unchanged `post-autoboot-p432-v1` selection does not admit the later
historical file set. The five-entry difference alone does not identify paths
or prove that a particular runtime file is now readable. A separate fixed
P441-pair acquisition must establish its actual contents after replay.
No deletion, wildcard admission or writer retry follows from the comparison.

The protected mount was unmounted, all children/descriptors settled and
partition RO confirmed before normal native CONTROL/Download return.
Replay/checker completion and clean superblock are proved; the selected
complete root and eligibility for another writable Debian boot are not.
Original A does not undo the native_data writes.

## Android return and evidence closure

Original A was transferred once. One post-A health read transiently failed;
the existing owner continued health verification only and closed through
`recovery-health`. There was no second transfer, writer invocation or control
replay. Exact boot/supporting partitions, changed Android boot identity, full
GPT and Android32 capacity of 34,357,624,832 bytes passed.

H0 closure rederived **600 raw captures** and the unchanged **20-row journal**,
validated the immutable candidate claim and source snapshot, and confirmed
`ANDROID_CLOSED_HEALTHY` with no active F1 owner. Device acquisition was blocked
during that audit; only the declared host ELF inspections were permitted.

Canonical elapsed timeline from the original grant:

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / done | 28.517 / 30.073 |
| Authenticated candidate ready / writer intent | 43.428 |
| Journal operation complete | 47.435 |
| Original-A transfer start / done | 56.019 / 57.620 |
| Original-A full health | 98.341 |
| Audited session close | 172.909 |

Private evidence:
`workspace/private/outputs/s22plus-journal-recovery-p443-h0-20261020-1/`,
including the operation's raw proof, terminal and task `closure-audit.json`.
The [P442 pre-replay capture](S22PLUS_AUTOBOOT_EVIDENCE_P442_RUN_2026-10-20.md)
and all consumed P441/P439 evidence remain unchanged.

A90 and S20+ received no command. Unrelated working-tree content was preserved.
P443 is closed and grants no replay or new writable experiment.
