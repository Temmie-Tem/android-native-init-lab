# S22+ P440: authenticated P437 runtime retrieved after replay

P440 consumed its returned one-operation, 1800-second attended grant on
2026-10-20 KST and closed **ANDROID_CLOSED_HEALTHY**. One N and one original A
were transferred, with no F1 owner remaining. A90 and S20+ were untouched.
The [preparation](S22PLUS_AUTOBOOT_EVIDENCE_P440_H0_2026-10-20.md) retains
independent review and actual artifact/VM qualification.

## Fixed acquisition and interpretation

The mountless reader completed **PASS_ROOT_EVIDENCE_OBSERVED** with partition
RO, no mount/replay/filesystem write and a settled child. The protected
superblock view was state 1, RECOVER 0, orphan head 0. Both selected files
were read in full, root-owned regular 0600 with one link:

| File | Bytes | Authenticated records | Result |
| --- | ---: | ---: | --- |
| P437 early | 10,972 | 14 | Complete preparation/client sequence through pre-unmount record |
| P437 runtime | 1,024 | 6 | Installed-init observation, START, rcS entry and fork boundary |

Raw files were saved before H0 interpretation. The current collector returned
**PASS_AUTHENTICATED_LOCAL_PROGRESS** with matching boot and nonce and no
trailing parse/authentication error. The early file is byte-identical to the
one retrieved by P438. The runtime file is now visible after P439's replay;
P438's earlier `ABSENT_IN_HOME_VIEW` remains correct for its original view.

Runtime records span device elapsed 6,147–6,173 ms. The highest authenticated
stage is **RCS_ENTERED**; the final record observes the fork result. This
corroborates first-boot installed-init/rcS progress. It does not prove child
exec success, rcS completion, service liveness, SSH or clean shutdown.
The pair belongs to the already observed first P437 boot; it supplies no new
second-boot progress record or watchdog-renewal cause.

This acquisition does not revise P439's `RECOVERY_NOT_PROVED` result or prove
complete current root consistency. The exact retrieved bytes and metadata
can be considered for a separately reviewed historical table, followed by
mandatory complete protected admission before any new writable lifetime.

## Original-A return and closure

Normal authenticated return and one original-A transfer completed. A single
post-A ADB read failure was preserved; the same owner performed health-only
continuation without another transfer. Full original partition/root health,
changed Android boot and Android32 GPT/capacity passed. The terminal retains
`recovered=true`.

H0 closure rederived 617 raw captures, the unchanged 20-row journal and terminal,
consumption and exact N/A counts with device/process acquisition blocked.
The 139-source host review snapshot and 165 runtime source copies preserve
execution provenance. File interpretation is a separate, raw-bound H0 result.

Canonical timeline, seconds from the original grant:

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / complete | 15.364 / 16.882 |
| Native ready and fixed read intent | 42.275 |
| Fixed read complete | 46.119 |
| Original-A transfer start / complete | 54.274 / 55.834 |
| Original-A final health proved | 104.300 |
| H0 audit and task close | 129.590 |

Private evidence:
`workspace/private/outputs/s22plus-autoboot-evidence-p440-h0-20261020-1/`.
`connected-prepared-1/task/closed.json` binds the consumed operation and
`closure-audit.json`; `retrieval-1/` retains both raw files and authenticated
interpretation. No remaining grant authorizes another device effect.
