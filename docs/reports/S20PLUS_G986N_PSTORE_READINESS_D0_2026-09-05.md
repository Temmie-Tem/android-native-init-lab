# S20+ G986N pstore/PMSG readiness D0

Date: 2026-09-05
Target: `SM-G986N / y2q / y2qksx / G986NKSS8IYC2`
Scope: H0 implementation/review/activation and one attended read-only D0
Terminal: **PASS_S20PLUS_G986N_PSTORE_READINESS_D0_OBSERVED**
Readiness: **METADATA_READY_RETENTION_UNPROVED**

## Outcome

One fixed S20+ root metadata read confirmed the static ramoops geometry from
the [preceding H0 audit](S20PLUS_G986N_EARLY_BOOT_OBSERVATION_H0_2026-09-05.md)
on the exact live target. The pstore backend and platform driver are ramoops,
pstore is already mounted, and the dynamic PMSG class/device numbers agree.
Public identity, healthy Android, enforcing SELinux and the current boot were
unchanged across the read. The fixed root prelude validated UID/GID 0, Magisk
30.7/30700 and stock PID1 before the additional metadata reads.

| Observation | Result |
| --- | --- |
| fixed DT compatible, region and four sizes | match the retained stock geometry |
| optional DT status properties | absent with accessible parent directories |
| ramoops reservation | 1,048,576 bytes |
| record, console, ftrace and PMSG configured zones | 262,144 bytes each, before headers |
| pstore backend / platform driver | ramoops / ramoops |
| pstore mount | present as pstore |
| PMSG class number and direct character-node number | equal; no major/minor was assumed |
| fixed console/PMSG/dmesg previous-record filenames | unavailable |
| `/proc/last_kmsg` | regular file, access check succeeded, size 2,097,136 bytes |
| two fixed watchdog attribute paths | absent; live watchdog state not established |

The record checks did not enumerate the pstore directory, so they do not
establish that the whole directory is empty. Access checks and file sizes do
not prove successful log-body retrieval. No previous-record or last_kmsg
content was opened or read. No marker was written, no reboot occurred, and
neither retention nor native PID1 execution was proved.

The six host commands were two global inventories and four exact-S20+
commands: devpath, public pre-snapshot, one fixed root script and public
post-snapshot. Root command count is one. Device effects, writes, reboots,
partition operations and S22+/A90/other-target commands are all zero.

## Fixed implementation

The new runner is
`workspace/public/src/scripts/revalidation/s20plus_g986n_pstore_readiness_d0.py`;
its tests are `tests/test_s20plus_g986n_pstore_readiness_d0.py`.
It accepts only `--render-plan` or `--connected`, with no caller-selected
serial, command, path, executable, callback or output destination. The
concrete backend validates one six-command sequence and derives its serial
only from the first exact inventory.

The runner reuses frozen root-health parsing and atomic evidence publication
utilities, without changing the existing root-health source or execution
owner. The corrected public exec-out quoting and root shell quoting remain
unchanged. New fixed declarations generate both the root-script calls and the
ordered parser surface. Each metadata file reads at most 65 bytes to enforce
a 64-byte accepted limit; the mount table reads at most 65,537 bytes to enforce
a 65,536-byte accepted limit. Log paths receive only type/access/size/link
checks. The root command has a 30-second timeout and an 8-KiB combined-output
limit. Missing or unreadable facts remain observations; unsafe node types,
oversized values, framing errors or identity drift close the invocation.

Source/contract activation is checked at the collection owner and concrete
backend. The backend also rejects any extra command or same-instance replay.
One direct attended request authorizes one invocation, not background polling.
The new [target-contract section](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-pstorepmsg-readiness-d0)
defines this D0 independently of root-health, P0, T2, autonomous research, R1
and F1. Their authority and consumed-candidate states remain unchanged.

## Independent review and failure capture

Independent review initially held activation for one P2 finding: the reused
inventory command helper discards partial output when it raises on timeout or
output overflow. This left the new root failure receipt without an output
digest despite a command having produced bytes.

The correction leaves frozen dependencies unchanged and adds bounded in-memory
prefix capture to this runner. On timeout or output overflow, it terminates
the single host client, retains only prefix sizes/hashes and stop/truncation
metadata, and publishes those facts in the private failure receipt. It never
publishes raw output or retries a command. Host subprocess fixtures reproduce
timeout, stdout overflow and stderr overflow, including root failure through
the actual private terminal publication path.

Re-review returned **PASS_GO**, with the P2 resolved and no remaining blocking
finding. It also covered the exact dormant-to-active boolean and target-section
status transition. Mechanical activation changed only those two atoms; the
normalized runner, root script and tests retained their reviewed hashes.
Review and activation contacted no device. The one subsequent D0 used the
operator's current direct request and its own fresh runtime binding.

| Reviewed input | SHA-256 |
| --- | --- |
| dormant runner | `2e0d4e9c4a2e0639072600465cb17334529cf2a4bb8cddbf15d76cc4c4dd104f` |
| active runner | `f1e61ec324b7c446ed73e14fe6318cf1a7488733b634861c6ffbbeb79001552b` |
| activation-normalized runner | `85d6da3729dbd7a9ef0e3af11fc0809103c4a32ef5cfd4348242ffa00e4e4ac7` |
| 5,284-byte fixed root script | `71c86ff82ddc9ea01e5532f489ae4843eee2429897fbaa7584cd4f87f309950c` |
| focused tests | `5563931dbcf50e38e1179630b9f4ef19b9d3202445aff8012f6dfb84caaee0b4` |
| unchanged root-health dependency | `24f69cc5aa43c70558e3594534ee684db0a038e972d1b0db2f1b8d8446af2d44` |
| unchanged inventory dependency | `3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81` |

## Validation and evidence

The new 18-test suite passed, including the actual shell producer against a
synthetic filesystem, parser and envelope failures, target ambiguity and boot
drift, symlink/FIFO/oversized inputs, bounded failure capture, privacy,
no-clobber evidence, dormant gates and activation identity checks. The reused
root-health and public-exec repair suites passed 50/50. Touched Python passed
`py_compile`.

The older onboarding suite passed 14/15. Its single failure asserts an obsolete
complete target-header string. The same assertion fails against the untouched
HEAD target contract; this unit did not change that header or the historical
test. This is not reported as a new profile failure or as an all-tests PASS.

Private qualification evidence:
`workspace/private/work/s20plus-pstore-readiness-d0-h0-20260905-v5ndx_dg/`.
Its `review.json`, `activation.json` and `plan.json` record the exact reviewed
and activated bytes. The D0 result binds its source version, dependencies,
tool identity, fixed script, current-target hashes and command counts.

Private run:
`workspace/private/runs/s20plus-g986n-pstore-readiness-d0/d0-19a938f3c46ba4e2b53c4f6a77669d4e/result.json`.
The 4,874-byte result SHA-256 is
`525fee589cb401a56d3091fa9bb954160df034a25589f152eef056217118bba3`.
Only typed facts and digests were retained; raw inventory, public snapshots,
root transcript and log contents were not published.

## Next research unit

Design and independently qualify one finite PMSG marker-retention experiment
through the intended return route, with a fixed marker and first-return reader.
PMSG writes and reboots are outside this read-only D0 and have no authority from
this result. A normal warm-reboot positive control would qualify only that
route; it would not establish preservation through Download, Odin, physical
power handling or recovery. The first returned kernel's old snapshot must be
read before another boot loses attribution. Only a route-matched positive
control can support a later new PID1 diagnostic candidate.
