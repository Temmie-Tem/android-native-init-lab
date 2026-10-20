# S22+ P439 strict recovery: replay/checker complete, root comparison negative

P439 consumed its returned one-operation, 1800-second attended grant on
2026-10-20 KST and closed **ANDROID_CLOSED_HEALTHY**. One N and one original A
were transferred; no F1 owner remains. A90 and S20+ were untouched.

The [qualified preparation](S22PLUS_JOURNAL_RECOVERY_P439_H0_2026-10-20.md)
retains the exact `post-autoboot-p432-v1` comparison and strict writer.
This new post-P437 journal operation does not repeat or revise P434.

## Filesystem result

The fixed operation completed within its original observation window:

| Evidence | Observed result |
| --- | --- |
| Initial superblock | state 1, RECOVER 1, orphan head 0 |
| Strict writer | stage 5, complete 1, error 0, I/O error 0 |
| Writes | 24 writes, 95,232 bytes |
| Writer/checker children | Settled and reaped; checker proved, status 0 |
| Post-replay superblock | clean 1, state 1, RECOVER 0, orphan head 0 |
| Selected immutable comparison | All 8,971 entries match, zero findings |
| Complete tree | 8,979 observed against 8,976 admitted entries |
| Cleanup | Partition RO restored, protected mount unmounted |
| Scientific verdict | **RECOVERY_NOT_PROVED**, complete root not admitted |

Three tree entries remain outside the selected finite accounting. This
aggregate observation does not identify their paths. Known later historical
records are outside the old comparison, but their current bytes and any newly
visible P437 runtime record require a separate fixed reader.

Writer completion, clean superblock and read-only checker success are proved.
Full-root consistency/admission and another writable Debian boot are not.
No deletion, general repair, wildcard allowance or replay retry followed.

## Return and closure

The settled result used the normal authenticated return and one original-A
transfer. The first final-health ADB read failed with a preserved
`RawCaptureError`. The same owner then performed only health continuation;
there was no additional transfer or replay. Full rooted original-A partition
hashes, a changed Android boot and Android32 GPT/capacity passed.
The terminal retains `recovered=true` for that health continuation.

The H0 closure rederived 617 raw captures, the original terminal, all required
steps and the unchanged 20-row journal with device acquisition blocked.
It verified the consumed candidate claim, one operation, N/A counts 1/1 and
absence of an F1 owner. Frozen runtime sources (169) and the current host
review snapshot preserve execution provenance. The single failed capture
remains in private evidence.

Canonical timeline, seconds from the original grant:

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / complete | 16.141 / 17.672 |
| Native authentication and writer intent | 42.729 |
| Fixed journal operation complete | 48.752 |
| Original-A transfer start / complete | 57.265 / 58.844 |
| Original-A final health proved | 107.209 |
| H0 audit and task close | 231.891 |

Private evidence:
`workspace/private/outputs/s22plus-journal-recovery-p439-h0-20261020-1/`.
The consumed task is `connected-prepared-1/task/`; its `closed.json` binds the
terminal, source snapshots and `closure-audit.json`.

Next is a fresh mountless reader of the same exact P437 early/runtime pair.
Its acquisition can inform precise historical admission for the planned
watchdog comparison; P439 grants neither that read nor a new writable boot.
