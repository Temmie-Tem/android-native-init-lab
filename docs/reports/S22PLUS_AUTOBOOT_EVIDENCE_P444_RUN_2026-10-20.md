# S22+ P444: authenticated P441 pair retrieved after replay

P444 consumed its returned one-operation, 1800-second attended grant on
2026-10-20 KST and closed **ANDROID_CLOSED_HEALTHY**. One N and one original A
were transferred, with no F1 owner remaining. A90 and S20+ were untouched.
The [preparation](S22PLUS_AUTOBOOT_EVIDENCE_P444_H0_2026-10-20.md) retains
independent review and actual artifact/VM qualification.

## Fixed acquisition and interpretation

The mountless reader completed **PASS_ROOT_EVIDENCE_OBSERVED** with partition
RO, no mount/replay/filesystem write and a settled child. It used 22 bounded
reads totalling 181,248 bytes. The protected superblock view was state 1,
RECOVER 0, orphan head 0. Both selected files were read in full with their
required root-owned regular 0600, single-link metadata:

| File | Bytes | Authenticated records | Result |
| --- | ---: | ---: | --- |
| P441 early | 10,972 | 14 | Complete preparation/client sequence through pre-unmount record |
| P441 runtime | 1,024 | 6 | Installed-init observation, START, rcS entry and fork boundary |

Raw files were saved before H0 interpretation. The current collector returned
**PASS_AUTHENTICATED_LOCAL_PROGRESS** with matching boot and nonce and no
trailing parse/authentication error. The early file is byte-identical to
[P442's original capture](S22PLUS_AUTOBOOT_EVIDENCE_P442_RUN_2026-10-20.md).
The runtime file is now visible after
[P443's strict replay](S22PLUS_JOURNAL_RECOVERY_P443_RUN_2026-10-20.md);
P442's earlier `ABSENT_IN_HOME_VIEW` remains correct for its original view.

Runtime records span device elapsed 6,510–6,536 ms. The highest authenticated
stage is **RCS_ENTERED**; the final record observes the fork result. Both
files match only the first of P441's two independently retained boot epochs.
They corroborate installed-init/rcS progress, but do not prove rcS child exec,
rcS completion, service liveness, SSH, clean shutdown, second-boot writes or
the cause of missed watchdog renewal.

This read does not revise P443's `RECOVERY_NOT_PROVED` result or prove complete
current root consistency. The retrieved bytes and metadata may support a
separately qualified history table; any new writable lifetime still requires
complete protected admission.

## Original-A return and closure

Normal authenticated return and one original-A transfer completed. One
post-A ADB read failure was preserved; the same owner performed health-only
continuation without another transfer or reader invocation. Full original
partition/root health, changed Android boot and Android32 GPT/capacity passed.
The terminal retains `recovered=true`.

H0 closure rederived 649 raw captures, the unchanged 20-row journal and
terminal, consumption and exact N/A counts with device/process acquisition
blocked. The frozen 139-source host review and 165 runtime source copies
preserve execution provenance. Pair authentication and first-epoch matching
are separate raw-bound H0 results.

Canonical timeline, seconds from the original grant:

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / complete | 22.895 / 24.434 |
| Native ready and fixed read intent | 49.695 |
| Fixed read complete | 53.549 |
| Original-A transfer start / complete | 61.819 / 63.407 |
| Original-A final health proved | 111.842 |
| H0 audit and task close | 119.420 |

Private evidence:
`workspace/private/outputs/s22plus-autoboot-evidence-p444-h0-20261020-1/`.
`connected-prepared-1/task/closed.json` binds the consumed operation and
`closure-audit.json`; `retrieval-1/` preserves both raw files, and
`p441-file-interpretation.json` binds their original capture and retained epochs.
The consumed grant authorizes no further device effect.
