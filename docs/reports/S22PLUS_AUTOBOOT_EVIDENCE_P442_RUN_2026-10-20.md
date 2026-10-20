# S22+ P442: P441 early file recovered; dirty runtime view remains incomplete

Status: **PASS_ROOT_EVIDENCE_OBSERVED / ANDROID_CLOSED_HEALTHY**.
Only `SM-S906N/g0q/S906NKSS7FYG8` was selected.

The operator returned the exact attended one-operation/1800-second grant for
the [qualified P442 reader](S22PLUS_AUTOBOOT_EVIDENCE_P442_H0_2026-10-20.md).
One fresh reader N transfer, one sealed pair acquisition and one original-A
transfer are consumed. The device returned to rooted Android32 with exact
boot/supporting partitions, changed Android boot identity, full GPT and
34,357,624,832-byte statfs health. No F1 owner remains.

## Acquired evidence

The reader retained partition RO, made no mount, replay or filesystem write,
and settled its unprivileged child. It made 21 bounded storage reads totaling
177,152 bytes. The superblock was state 1, RECOVER 1, orphan 0: the source view
was dirty checkpointed home blocks without journal replay.

- Early file: **10,972 bytes**, captured in full. All **14 records** authenticate,
  with no malformed tail, through `EARLY_PRE_UNMOUNT`.
- Runtime file: **ABSENT_IN_HOME_VIEW**. There are no runtime bytes to authenticate
  and no early/runtime boot-and-nonce join.

The early file's authenticated boot identity matches only the first of the two
retained [P441 boot epochs](S22PLUS_AUTOBOOT_WATCHDOG_P441_RUN_2026-10-20.md).
It does not prove unmount return, installed services, same-boot SSH or clean
shutdown. The missing runtime home-block path does not erase P441's separately
authenticated installed-PID1/rcS records and does not prove non-execution.
Second-boot writes or safe rejection remain unproved.

Raw acquisition and the complete captured file were preserved before decoding.
H0 rederivation blocked process/device acquisition and left the consumed P441
and P442 journals and terminals unchanged.

## Return and closure

Native health/CONTROL and measured Download return completed. Original A was
transferred once. One post-A health read transiently failed; the existing owner
continued only health verification and closed through `recovery-health`.
It did not repeat either image transfer or the reader invocation.

H0 closure rederived **649 raw captures**, the unchanged **20-row journal**,
exact N/A ownership, final health and the absence of an active F1 owner.
Execution sources, capability and the close/interpretation code are pinned in
the private evidence directory.

Canonical elapsed timeline from the original grant:

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / done | 20.674 / 22.204 |
| Authenticated candidate ready | 47.123 |
| Fixed read complete | 50.653 |
| Original-A transfer start / done | 58.831 / 60.401 |
| Original-A full health | 108.226 |
| Audited session close | 126.804 |

Private evidence:
`workspace/private/outputs/s22plus-autoboot-evidence-p442-h0-20261020-1/`,
including `connected-prepared-1/task/closure-audit.json`, `retrieval-1/` and
`p441-file-interpretation.json`.

Current native_data consistency is not established. A later strict journal
recovery, post-replay reader and writable-root admission are separate actions
under their own current bindings and grants. P442 cannot be replayed.
A90 and S20+ received no command; unrelated working-tree content was preserved.
