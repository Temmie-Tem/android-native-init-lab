# S22+ P438: P437 early file recovered; runtime absent in dirty home view

Status: **PASS_ROOT_EVIDENCE_OBSERVED; ANDROID_CLOSED_HEALTHY**.
P438 is consumed and closed after one reader N and one original-A transfer on
2026-10-20 (Asia/Seoul). No F1 owner remains. A90 and S20+ received no command.

The fixed reader recovered P437's complete 10,972-byte early file. The physical
writer's key and measured sources authenticate all 14 records, 76 preparation
module completions and six later client returns. Its boot identity matches
the first P437 candidate boot in the preserved retained-log analysis, which
later reached installed Debian PID1 and suffered the watchdog reset. It does
not match the second candidate boot. The original retained raw and epoch
slice hashes were verified before this comparison.

The sealed runtime path returned `ABSENT_IN_HOME_VIEW`. The reader observed
`state=1 recover=1 orphan=0`: a dirty, unreplayed home-block view. This absence
does not prove that the runtime file was never created or that installed init
did not run. P437's separately authenticated RAM evidence of installed PID1,
rcS fork and checked runtime-record write/fsync/readback/close remains valid.
The runtime file may be represented only in journal updates; this read does
not establish that explanation or the second boot's write effects.

## Evidence and limits

The H0 collector preserved the acquisition and complete early bytes before
interpretation, then authenticated them against the actual physical P437
artifact. It reports `PASS_AUTHENTICATED_LOCAL_PROGRESS`, highest stage
`EARLY_PRE_UNMOUNT`, and no malformed tail. The early records span 2,481 through
2,590 ms of P437's original kernel BOOTTIME. Runtime is `NOT_CAPTURED` and the
early/runtime boot-and-nonce join is `UNAVAILABLE`.

This file independently establishes measured initial Debian PID1 and the
completed early preparation/record sequence. It does not itself prove an
unmount return, installed Debian PID1, rcS completion, services, SSH or clean
shutdown. The earlier RAM evidence supplies its own, separate installed-PID1
and child-progress claims. Missing records are not non-execution evidence.

The reader retained partition RO, made 21 bounded library reads totaling
177,152 bytes, mounted no filesystem, replayed no journal, wrote no filesystem
data and executed no installed program. Original Android health after return
does not make native_data clean. The fixed two-file read also does not
enumerate or qualify the complete installed root.

The [P437 terminal](S22PLUS_P437_RCS_OBSERVATION_RUN_2026-10-19.md) remains
consumed `NO_PROOF / ANDROID_CLOSED_HEALTHY`. Its
[two-boot/watchdog analysis](S22PLUS_P437_BOOT_REQUIREMENTS_WATCHDOG_H0_2026-10-19.md)
is supplemented by this first-boot file match, without merging the boots or
revising any historical terminal. The second boot's native_data effects remain
unknown. The inactive watchdog observer has not been booted by P438.

## Authority, original-A return and timeline

The operator explicitly confirmed attendance and usable physical Download
recovery, and returned the exact one-operation/1800-second approval. Before
opening that grant, the current task, dedicated review, host/runtime source
snapshot and absence of a global F1 owner were revalidated. Execution used
[P438's qualification](S22PLUS_AUTOBOOT_EVIDENCE_P438_H0_2026-10-19.md), base
commit `d5ba5668ec3da745e9fa42fab57a807b82d3dd68`, and its frozen reviewed
working-tree sources. Fresh target, health, artifact and recovery checks passed.

The owner performed one N transfer, authenticated native health, sent one
fixed reader EXEC, captured its result and closed the descriptor after DETACH.
Same-boot native CONTROL reached Download and one original-A transfer completed.
One initial post-A ADB health read failed; its raw evidence was preserved and
the existing recovery path continued health checks only. No second transfer,
reader invocation, reboot or manual Download step was needed.

Final health proves a changed Android boot, exact original boot/supporting
partitions, root, unchanged retained GPT and Android32 capacity of
34,357,624,832 bytes. The terminal is `ANDROID_CLOSED_HEALTHY`,
`research_closed=true`, `recovered=true`; the latter records health continuation.

| Event | Seconds from P438 grant opening |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer intent | 19.410 |
| Candidate transfer complete | 20.933 |
| Native health proved / reader intent | 45.846 |
| Fixed read complete | 49.384 |
| Original-A transfer intent | 57.364 |
| Original-A transfer complete | 58.955 |
| Final Android health complete | 106.937 |
| Session close and H0 audit | 111.052 |

## Closure and next bounded work

H0 closure rederives initial/final health, the consumed N/A pair, read, normal
return and terminal from retained evidence with process/device acquisition
blocked. It audits 649 raw captures and the one transient read failure,
verifies the source snapshot and consumed claim, and leaves all 20 journal
rows and the original terminal unchanged. The one-operation budget is spent.

Private source snapshots, approval, raw acquisition, early file, epoch join,
closure audit and structured close record remain under
`workspace/private/outputs/s22plus-autoboot-evidence-p438-h0-20261019-1/`.
The existing reader qualification is unchanged; this reporting update needs
content/link/diff/boundary checks, not another image build or device read.

The next useful host-only work is to assess the existing fixed journal-recovery
and exact historical-file admission paths against this concrete dirty result.
P437's early file now has exact physical bytes; its runtime file remains
unavailable for exact admission. The existing clean-root requirement blocks
another writable Debian candidate. This result authorizes no replay, repair,
deletion, wildcard admission or further writable boot. A future recovery or
watchdog candidate needs its applicable qualification and authority separately.
