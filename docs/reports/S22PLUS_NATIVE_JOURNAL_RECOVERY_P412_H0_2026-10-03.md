# S22+ P412 native_data journal recovery H0

Date: 2026-10-03 KST. Target: `SM-S906N/g0q/S906NKSS7FYG8` only.
Candidate: **P412 `v0.4.0-rc.12`**.

Historical H0 snapshot. The later
[physical operation](S22PLUS_NATIVE_JOURNAL_RECOVERY_P412_FIRST_RUN_2026-10-03.md)
consumed this candidate, proved clean protected-root admission and closed
healthy Android. Its final health routing correction and independent H0
closure review are recorded separately; the original source pins below remain
unchanged and grant no further execution.

## Result and scope

The new [fixed journal-recovery capability](../operations/S22PLUS_NATIVE_JOURNAL_RECOVERY_V1.md)
has an actual byte-identical A/B boot-only package, a pinned static ARM64
replayer, protected post-replay admission and bounded original-A return.
Independent review returned **PASS_GO** and concrete offline preparation
completed **READY_H0_PRELIVE_ONLY**. This report is H0 evidence only: no connected read, control,
transfer, filesystem write, device grant or new native boot was performed.
A90 and S20+ were untouched.

P411 remains consumed and closed `ANDROID_CLOSED_HEALTHY`. Its last protected
observation was `clean=0 state=1 recover=1 orphan=0`; it did not mount or
execute Debian. Current Android health and native_data state were not
reobserved in this work. The new capability is not a P411 retry or proof that
the physical filesystem has been repaired.

## Why the fixed tool is separate

The retained e2fsprogs 1.47.2 checker is appropriate for the protected `-fn`
check, but its `-E journal_only` option is not a replay-only write boundary.
The actual source can restore the journal inode from backup, repair journal
metadata, reach orphan cleanup, reset journal state after an error and later
return zero. Those paths were reviewed before choosing a writer.

The separate strict entry reuses the upstream JBD2 scan/revoke/replay code
while bypassing ordinary e2fsck command parsing, configuration, restart and
repair. It validates the sealed filesystem and internal checksummed journal,
uses uncached partition-bounded I/O, rejects journal self-targets and latches
I/O failure. Successful finalization changes only the journal head/sequence/
checksum and primary RECOVER/checksum fields, with checked flush and full
block readback. It performs no orphan cleanup, other fsck repair or mount.

Its parent uses the existing authenticated native owner and child settlement
engine. After conclusive writer exit and descriptor closure it restores only
native_data RO, runs the separate pinned `e2fsck -fn`, then compares the full
P401 archive under a protected noload/noexec mount. The only accepted mutable
data are the already declared finite P410 lifetime paths/bounds. No installed
program, Debian init, service, USB gadget transition or SSH is executed.

## Validation

| Evidence | Result and limit |
| --- | --- |
| Actual ARM64 regular-file tool tests | 29 cases passed: committed replay, revoke, uncommitted tail, primary/journal/inode rejection, replay-revealed orphan, checksums, write bounds, short/failed writes, flush/readback/close failures |
| Actual ARM64 kernel VM | Six final cases passed: replay, clean skip, initial orphan, replay-revealed orphan, corrupt journal, completed replay followed by checker rejection |
| Child-failure ARM64 VM | Seven cases passed: setup failure, early zero, timeout, signal, overflow, impossible zero-write success, descendant during checker; outer group settlement proved and no result promoted |
| Unit and real C/PTY observation | 92 focused tests passed, including the actual common 300-second observation path, pre-EXEC intent, DETACH and transcript rederivation |
| Repository boundary regressions | 12 tests passed; boundary scan clean before staging, repeated over the final selected tracked files |
| C/Python build checks | Static AArch64 ELF checks, helper A/B equality, package A/B equality and touched-Python compilation passed |

Every VM kept bytes outside native_data unchanged. The normal paths restored
partition RO while leaving LU0 and userdata RO settings unchanged. Successful
replay passed the separate checker and all **8,969** archive entries, including
**8,175** boot-relevant entries, with the declared mutable-data accounting.
These are real ARM64 VM/kernel results, not Samsung storage/USB proof.

The corrupt payload test intentionally retained a partial negative: one valid
later block was replayed, the corrupt block was skipped, and finalization did
not occur. The out-of-range test used a valid committed descriptor with its
target changed and checksum recomputed; it reached replay stage 2, failed the
I/O bound with zero writes and kept the image unchanged. An earlier fixture
was rejected by debugfs before producing that transaction and was not used
as the final boundary proof.

Independent review also found and resolved two evidence/integration errors:
impossible successful write counts were accepted by the first decoder, and
the common observer initially lacked the new profile's 300-second routing.
Native/Python accounting now requires both finalization writes, and the
actual C/PTY test exercises the corrected common observer.

One broader optional historical-artifact test rejected the retained P391
runtime because its stored `s22plus_native_thermal_build_v1.py` source pin
differs from the current file. That file was not changed by P412. The retained
P391 artifact/pin was preserved; this is separate from the 92 passing focused
tests and the successful current P412 A/B audit.

## Actual artifacts and retained evidence

The private root is
`workspace/private/outputs/s22plus-journal-recovery-p412-h0-20261003-1/`.
No firmware, generated seal, device identifier, raw capture or compiled payload
is included in the commit.

| Artifact | Size / SHA-256 |
| --- | --- |
| Strict target replayer | 1,728,736 bytes / `823ffaedac358589237c5a7b9e8d82f04c4aba3425a8a5c4651f3bf4482bdb64` |
| Native recovery helper | 923,096 bytes / `40eb1e4cad35fef952a87d44e87e45e5538a071add84d0f1cbb504464f63d683` |
| A/B boot-only AP | 33,853,481 bytes / `85395f4ecb93fc0720d1690d9a98d329a97cb494b850b5870cfcb07475922afc` |
| Qualified image record | `db16369fe86c77dc4e7f7373359bac3414cfa05604189b1d6c79cdaabaeb5609` |
| Final tool qualification | `4ffe603fbe4f5c7c2007f1c378cc4b732338d6621ca81c236434b45944f78d20` |
| Frozen review closure | `b88cf431f8314f918056a11ece1a54d9b7ae1c5f0910791cb1728143ed9e8401` |

The review input contains 93 host source pins and 168 runtime source pins.
Their 247-file union plus five test/fixture files are preserved as a 252-file
snapshot. Actual tool source/build inputs, all final VM logs, helper output,
regular-file failure images/results and artifact qualification remain private.
The original P411 terminal, authenticated preparation log and closed record
were rehashed unchanged.

Helmholtz independently verified 621 pinned paths, the actual A/B boot/AP
contents and current image binding, then returned source-bound PASS_GO with
no unresolved findings. The dedicated
[capability record](../../workspace/public/src/device-action/bindings/s22plus_native_journal_recovery_v1_review.json)
does not repin any consumed review or run.

Offline preparation produced task SHA-256
`ac27dff2ef793ed5196247f5b6195f15b9938a124a64e8aeaa603e509a576cc1` and ready
record `4849de05b25fb928f42c95a28537e77b0454a197a7148188d9f007b386f25395`.
The harness disabled device command capture, Android commands, live lane
capture/revalidation, host-device opening and grant creation. Only the exact
local `file`/`readelf` inspections of the pinned replayer were allowed.
Policy validation passed; no grant file exists, the candidate is unclaimed,
and the F1 owner is absent. Fresh connected health and current native_data
admission remain explicitly unproved.

## Next physical scope

The proposed physical operation is one attended `journal-recovery` grant of
at most 1800 seconds: fresh exact Android preparation, one N, one strict replay
attempt if eligible, protected checker/root admission, then one original-A
return and complete Android32/GPT health. Incomplete/uncertain results require
the already bound attended physical recovery without another writer attempt.

Original A does not roll back native_data. A partial replay may leave Debian
data needing a separately scoped repair, even when Android returns healthy.
Only after a closed physical recovery and proved clean/exact root should a
fresh Debian handoff candidate resume rcS/service/NCM/SSH qualification.
