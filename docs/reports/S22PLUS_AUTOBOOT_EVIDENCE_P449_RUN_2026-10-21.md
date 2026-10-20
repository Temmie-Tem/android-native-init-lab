# S22+ P449: P448 early file recovered from a dirty home-block view

Status: **PASS_ROOT_EVIDENCE_OBSERVED / PASS_AUTHENTICATED_LOCAL_PROGRESS /
ANDROID_CLOSED_HEALTHY**. Only `SM-S906N/g0q/S906NKSS7FYG8` was selected.

The approved fixed reader consumed one P449 N and one original A. It recovered
P448's complete 10,972-byte early file. All 14 records authenticate through
`EARLY_PRE_UNMOUNT`, with no torn tail. The runtime file is
`ABSENT_IN_HOME_VIEW`; it was not recovered. The observed native_data
superblock is `state=1, recover=1, orphan=0`, so the checkpointed home-block
view still requires journal recovery and does not establish filesystem
consistency. No mount, journal replay, filesystem write or installed execution
occurred in P449.

The original [P448 physical result](S22PLUS_AUTOBOOT_SINGLECPU_P448_RUN_2026-10-21.md)
and its consumed grant remain unchanged. The
[P449 qualification](S22PLUS_AUTOBOOT_EVIDENCE_P449_H0_2026-10-21.md)
retains actual A/B packages, two fresh ARM64 cases, 33 focused tests and
source-bound independent PASS_GO. This physical reader used that exact task.

## Acquired evidence and interpretation

The fixed reader confirmed exact partition identity and retained partition RO.
It read only the sealed early/runtime pair, without mounting or replaying JBD2.
The H0 collector saved acquisition metadata and the entire captured early
file before interpreting either file. A missing peer did not discard the
valid early chain.

The early file authenticates measured Debian initial PID1, 76 preparation
module completions and six later client attempts/returns. Its final record
precedes unmount; the file alone does not prove the later unmount return,
installed init, rcS completion, services, SSH or clean shutdown.

Re-decoding the original P448 retained bytes joins this file to the first of
the two authenticated P448 boots, and excludes the second. The first boot's
158 preparation and 131 strict transition records rederive; its already proved
installed Debian PID1 and rcS fork remain separate retained evidence. The
second boot's 156 preparation records remain distinct. This acquisition does
not locate a reset or establish its cause, timing or relation to physical
recovery.

No early/runtime boot-and-nonce join is available because runtime was absent
from this view. Committed journal-only directory, inode or data changes can
be invisible without replay; absence is not non-execution. Android recovery
does not clean or roll back native_data. No missing runtime bytes are invented
or admitted to a historical root table.

## Return and closure

The normal native health/CONTROL return and original-A transfer completed.
One ADB read failed during post-A health. The existing owner preserved that
failure and continued only health observation, with no repeated transfer,
reader invocation or control action. Full changed-boot rooted Android health,
unchanged GPT and Android32 capacity of 34,357,624,832 bytes then passed.

H0 closure rederived all **628 raw captures**, the one preserved transient
read failure and the unchanged **20-row journal** with process/device
acquisition disabled. The terminal is `ANDROID_CLOSED_HEALTHY`, recovered
true because health continuation was used. The grant is closed and no F1
owner remains. One N and one A are permanently consumed.

| Canonical event | Seconds from grant opening |
| --- | ---: |
| Live session start | 0.000 |
| Candidate flash start / done | 19.333 / 20.878 |
| Authenticated reader ready | 46.144 |
| Fixed read complete | 49.791 |
| Original-A flash start / done | 58.465 / 60.055 |
| Final Android health proved | 99.960 |
| Audited task close | 119.926 |

The source snapshot binds the current host capability plus the reader runtime
and collector. Private evidence is under
`workspace/private/outputs/s22plus-autoboot-evidence-p449-h0-20261021-1/`:
the original operation/journal, `closure-audit.json`, `closed.json`,
`retrieval-1/` and `p448-file-interpretation.json`. The execution base commit is
`ae14d37bdb`; original consumed source and raw evidence remain preserved.

## Selected next bounded unit

Prepare a fresh operation under the existing
[fixed native_data journal-recovery profile](../operations/S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md),
then use a separate fixed reader after its healthy closure to recover the
same P448 pair. This takes priority over another writable Debian boot because
current native_data is dirty and the runtime file's visibility is unresolved.

The observed three superblock fields are not complete writer eligibility.
Fresh exact identity, checksum/features, journal bounds, zero error state,
current source-bound review, qualification and the returned attended grant
remain required. Only the strict committed-block replay is selected; general
repair, deletion, installation and replay retry are excluded. Replay/checker
completion, complete root admission and Android health must remain separate.
Unexpected entries after replay require retrieval and qualification, not
wildcard admission or removal. A subsequent functional boot candidate will
be selected from the completed file evidence and current root admission.

No new device grant is opened by this decision. P448, P449 and earlier recovery
operations remain consumed. A90 and S20+ were untouched.
