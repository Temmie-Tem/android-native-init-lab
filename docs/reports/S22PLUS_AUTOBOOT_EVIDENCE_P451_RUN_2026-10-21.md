# S22+ P451: authenticated P448 pair retrieved after replay

P451 consumed its returned one-operation, 1800-second attended approval on
2026-10-21 KST and closed **ANDROID_CLOSED_HEALTHY**. One N and one original A
were transferred, with no F1 owner remaining. A90 and S20+ were untouched.
The [preparation](S22PLUS_AUTOBOOT_EVIDENCE_P451_H0_2026-10-21.md) retains
independent review and actual artifact/VM qualification.

The operator used the independently reviewed terminal entry point because
the agent process could not run the mandatory privileged host census. Before
opening P451's original grant, that entry point rederived the exact
[P450 healthy closure](S22PLUS_JOURNAL_RECOVERY_P450_RUN_2026-10-21.md), checked
the same target and original A, then invoked the unchanged grant opener and
original reader CLI. No check was bypassed and no P450 effect was repeated.

## Fixed acquisition and interpretation

The mountless reader completed **PASS_ROOT_EVIDENCE_OBSERVED** with partition
RO, no mount/replay/filesystem write and a settled child. It used 22 bounded
reads totalling 181,248 bytes. The protected superblock view was state 1,
RECOVER 0, orphan head 0. Both selected files were read in full with their
required root-owned regular 0600, single-link metadata:

| File | Bytes | Authenticated records | Result |
| --- | ---: | ---: | --- |
| P448 early | 10,972 | 14 | Complete preparation/client sequence through pre-unmount record |
| P448 runtime | 1,024 | 6 | Installed-init observation, START, rcS entry and fork boundary |

Both raw files were saved before H0 interpretation. The unchanged collector
returned **PASS_AUTHENTICATED_LOCAL_PROGRESS** with matching boot and nonce,
complete captured framing and no trailing parse/authentication error. The
early file is byte-identical to [P449's pre-replay capture](S22PLUS_AUTOBOOT_EVIDENCE_P449_RUN_2026-10-21.md).
Runtime is now visible after P450's strict replay; P449's earlier
`ABSENT_IN_HOME_VIEW` remains correct for its original dirty home-block view.

Runtime records span device elapsed 15,390–15,448 ms. The highest authenticated
stage is **RCS_ENTERED** and the last record observes the rcS child fork.
The revision-6 platform record supplies one sample reporting CPU0 online and
the watchdog driver enabled. It does not prove continuous CPU state, actual
hardware watchdog renewal, or the required 120-second service window.

Both files match only the first of P448's two retained boot epochs. The join
was rederived from the original bounded raw retention spans and unchanged
primary/strict transition decoders, not just a cached boot label. The files
corroborate installed-init/rcS progress; they do not themselves prove rcS child
exec, rcS completion, service liveness, SSH, clean shutdown, second-boot writes
or the reset's timing/cause. P448's separately authenticated retained progress
keeps its existing meaning.

This acquisition does not revise P450's `RECOVERY_NOT_PROVED` verdict or prove
complete current-root consistency. New writable-root admission still requires
qualified current historical-file accounting and complete protected checks.
No new writer or replay was selected by this read.

## Original-A return and closure

The fixed authenticated return and one original-A transfer completed. One
post-A ADB read failure was preserved; the same owner performed health-only
continuation without another transfer or reader invocation. Full original
partition/root health, changed Android boot and Android32 GPT/capacity passed.
The terminal retains `recovered=true`.

H0 closure rederived **616 raw captures**, the unchanged **20-row journal** and
terminal, consumption and exact N/A counts with device/process acquisition
blocked. Frozen host, runtime and collector sources preserve provenance.
Pair authentication and first-boot matching are separate raw-bound H0 results.
Both P450 and P451 tasks are closed and their grants consumed.

Canonical timeline, seconds from the original grant:

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Candidate transfer start / complete | 15.420 / 16.940 |
| Native ready and fixed read intent | 42.038 |
| Fixed read complete | 45.881 |
| Original-A transfer start / complete | 53.851 / 55.423 |
| Original-A final health proved | 103.914 |
| H0 audit and task close | 130.071 |

Private evidence:
`workspace/private/outputs/s22plus-autoboot-evidence-p451-h0-20261021-1/`.
`connected-prepared-1/task/closed.json` binds the consumed operation,
predecessor and `closure-audit.json`; `retrieval-1/` preserves both raw files,
and `p448-file-interpretation.json` binds their original capture and retained
boot epochs. The consumed grants authorize no further device effect.
