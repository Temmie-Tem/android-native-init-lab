# S22+ P436: P432 installed Debian PID1 and rcS child fork recovered

Status: **PASS_AUTHENTICATED_LOCAL_PROGRESS; ANDROID_CLOSED_HEALTHY**.
The separately approved P436 reader is consumed and closed. Execution date:
2026-10-18 (Asia/Seoul). No F1 owner remains; A90 and S20+ received no command.

P436 recovered P432's unchanged 10,972-byte early file and a 1,024-byte runtime
file that was absent from P433's earlier dirty home-block view. Both files
authenticate against the physical P432 run, key and measured sources, and
their boot and nonce identities match. The new runtime evidence proves the
installed Debian PID1 and a successful fork for the rcS child. It does not
prove that the child executed rcS, that rcS completed, or that services ran.

The [P432 terminal](S22PLUS_DEBIAN_AUTOBOOT_P432_RUN_2026-10-18.md) remains
`NO_PROOF / ANDROID_CLOSED_HEALTHY`. This later, separately owned acquisition
adds historical progress proof without changing that terminal or replaying
its candidate. P436 itself executed only the fixed mountless reader.

## Recovered runtime and exact meaning

The runtime file contains one authenticated 256-byte header and six complete
128-byte chained records, with no malformed tail. Times below are milliseconds
of P432's original kernel BOOTTIME, not P436's clock or measured stop times.

| Record | Time (ms) | Established meaning |
| --- | ---: | --- |
| INIT | 6,045 | The installed hook passed actual PID1, root, init and hook identity checks |
| START | 6,046 | Automatic local startup reached the init barrier's release sequence |
| PROGRESS, phase 1 | 6,059 | The installed hook entered its rcS observation phase |
| BOUNDARY, phase 1/event 1 | 6,060 | The hook reached the pre-reporting-check boundary |
| BOUNDARY, phase 1/event 2 | 6,066 | Actual-init and absent-reporting-descriptor checks returned |
| BOUNDARY, phase 1/event 3 | 6,067 | The parent received a successful fork result for its rcS child |

The production collector's highest stage is `RCS_ENTERED`. Here that label
means the **hook's rcS phase**, not evidence that `/etc/init.d/rcS` executed.
The physical P432 build's frozen producer is authoritative: event 3 is emitted
by the parent after `fork()`. The child still has descriptor cleanup, deadline
checks and `execv()` on its separate path. No authenticated child-wait or
child-exit record was recovered, and there is no rcS/rc2 completion, local
service observation, NCM/SSH access or clean-shutdown proof.

P432's automatic variant has no reporting transport or host START request in
these hooks. Its reporting-open/close helpers check that descriptor 3 is absent.
The legacy boundary names therefore establish neither an ACM close/reopen nor
a host acknowledgment. The START record is automatic local progress.

The INIT predicate binds `/proc/1/exe` to the hash-checked installed init,
matches PID1's root with the native_data root, verifies the running hook and
checks the expected descriptor/namespace conditions. Together with the exact
physical producer and the joined early record, this supplies the installed
Debian host-PID1 evidence missing from the earlier P433 acquisition.

The early file still authenticates initial Debian PID1, all 76 preparation
module completions, six later client returns and all 14 early records. The
runtime proof shows that P432 progressed beyond the early file's close/unmount
interval and through its automatic installed-init transition. The early-only
projection correctly retains `unmount_return_proved=false`: it has no direct
unmount-return record, and its original meaning is not rewritten.

The final runtime timestamp is sampled before that record's write, fsync,
readback and close. Its recovered bytes do not prove that all of those calls
returned. The next unobserved interval includes that recording tail and the
parent's wait loop, alongside the child's cleanup/exec path. Missing later
records identify neither the failing syscall nor an actual halt. Persistence
or observation loss must remain distinct from non-execution.

## Filesystem evidence and remaining admission

The protected reader observed `state=1 recover=0 orphan=0`, retained partition
RO and performed 22 bounded library reads totaling 181,248 bytes. It mounted
no filesystem, replayed no journal, wrote no filesystem data and executed no
installed Debian program. The early file is byte-identical to P433's copy.

P433's `ABSENT_IN_HOME_VIEW` remains correct for its dirty view. P436 establishes
that the sealed runtime file is now present and authenticated after
[P434's journal operation](S22PLUS_JOURNAL_RECOVERY_P434_RUN_2026-10-18.md).
This is not a claim that P434 created the file or that absence meant it never
existed. The fixed two-file read does not enumerate the entire tree.

P434's 8,977-versus-8,976 complete-tree mismatch and `RECOVERY_NOT_PROVED`
remain unchanged. The recovered runtime file provides a concrete input for
future exact accounting, but neither the clean superblock nor this pair alone
qualifies the complete selected root. P435 remains unstarted, with its old
current-host review stale. No wildcard admission, deletion, repair, further
journal replay or writable boot is authorized by this result.

## Authority, return and canonical timeline

The operator returned the exact prepared one-operation/1800-second attended
approval in response to the physical-attendance/Download-recovery prompt.
Execution used [P436's qualification](S22PLUS_AUTOBOOT_EVIDENCE_P436_H0_2026-10-18.md)
at base commit `cc1d317912a31995b09ac67d72c1fca29982b1b3`, the reviewed frozen
working-tree sources, unchanged actual package and exact original-A artifact.
Current target, health, capability, artifact and recovery checks passed.

The owner transferred N once, authenticated native health, sent one fixed
reader EXEC, completed capture and DETACH, authenticated the same boot for
normal return and transferred original A once. One initial post-A health
read reported that the selected ADB device was not found. Its raw failure is
preserved; the existing recovery path continued health checks only. There
was no second A transfer, reboot, reader invocation or manual Download step.

Final health proves a changed Android boot, exact original boot/supporting
partitions, root, matching GPT and Android32 capacity of 34,357,624,832 bytes.
The terminal is `ANDROID_CLOSED_HEALTHY`, `recovered=true`,
`research_closed=true`; recovery bookkeeping describes the health continuation.

| Event | Seconds from P436 grant opening |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer intent | 18.075 |
| Candidate transfer complete | 19.561 |
| Native health proved / fixed reader intent | 44.621 |
| Fixed read complete | 48.463 |
| Original-A transfer intent | 56.618 |
| Original-A transfer complete | 58.172 |
| Final Android health complete | 106.505 |
| Session close and H0 audit | 130.531 |

## Verification and bounded next work

H0 closure rederives initial/final health, both transfers, the fixed read,
normal return and terminal from retained evidence, with process/device
acquisition disabled. It audits 616 raw captures, preserves the one transient
health-read failure, verifies frozen sources and the consumed claim, and
leaves the original journal and terminal unchanged. The one-operation budget
is exhausted and no F1 owner remains.

The H0 collector verifies both closed owners and the physical P432 artifact,
saves acquisition/raw files before parsing, authenticates both chains and
checks their boot/nonce join. Source interpretation verifies all 142 frozen
P432 build inputs and the actual hook/witness artifacts. It uses P432's frozen
producer, not the later P435 instrumentation. No execution code, parser,
historical terminal or capability review was changed to obtain this result.

Private acquisition, raw files, source mapping and closure records remain in
`workspace/private/outputs/s22plus-autoboot-evidence-p436-h0-20261018-1/`.
The report/goal update needs content, link and diff/boundary checks; unchanged
reader qualification and its prior tests are retained without another build.

The next bounded H0 unit is exact root accounting for the recovered runtime
file and the smallest useful rcS child/progress observation for the service
goal. Initial file-close-to-installed-init reachability now has physical
evidence; detailed failure attribution is still open. Any future device unit
needs its own applicable current qualification and authority. This consumed
reader and the earlier writer/recovery operations cannot be replayed.
