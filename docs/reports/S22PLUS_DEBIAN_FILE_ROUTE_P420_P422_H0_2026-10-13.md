# S22+ native_data consistency and USB-independent file evidence

**Subsequent physical results:** P420 consumed its one attended operation on
2026-10-13 KST and proved **PROVED_CLEAN_ROOT**, then returned original Android
healthy. See the [physical report and timeline](S22PLUS_NATIVE_DATA_P420_RUN_2026-10-13.md).
P421 then consumed its separate file-pilot operation and returned Android
healthy, with [file evidence pending at its own closure](S22PLUS_DEBIAN_FILE_P421_RUN_2026-10-13.md).
P422 subsequently consumed its separate reader grant: the exact P421 file was
absent in a clean superblock view, the collector returned **NO_AUTHENTICATED_FILE**,
and Android returned healthy. See the [retrieval report](S22PLUS_DEBIAN_FILE_P422_RETRIEVAL_2026-10-13.md).
All three candidates are consumed and closed. The preparation status and
unopened-grant statements below describe the preceding H0/D0 milestone;
they do not reopen any operation.

Status: **READY_H0_QUALIFIED; first Android D0 preparation passed**.
Independent PASS_GO is complete. No F1 grant, control, transfer or native_data
operation has occurred for this route.

The operator requested native_data consistency first, USB-independent file
logging under initial Debian ownership, and retrieval of the same run after
Android recovery. This report binds only `SM-S906N/g0q/S906NKSS7FYG8`.
A90 and S20+ are untouched. P419 remains consumed and closed healthy; its
USB timeout did not reveal the internal failure stage. P415's dirty
`state=1/recover=1/orphan=0` observation is historical, not a current check.

## Three separately owned operations

| Candidate | Purpose | Admission and closure |
| --- | --- | --- |
| P420, `v0.5.0-rc.4` | Fresh strict native_data consistency/recovery | Fixed protected dirty/clean decision; skip replay when clean; only the existing strict replay when eligible; complete protected root admission and original-A health |
| P421, `v0.5.0-rc.5` | Initial-Debian-PID1 file pilot | Fresh clean protected root admission, one exclusive file, one unmount attempt, then physical original-A return and full Android32 health |
| P422, `v0.5.0-rc.6` | Later exact-file retrieval | Separate native boot after P421's healthy Android closure; mountless partition-RO reader sealed to P421's run, then its own original-A closure |

P420 must establish its full existing success predicate before advancing.
Neither a clean superblock alone nor a healthy Android return substitutes for
complete root admission. Unexpected mutable-root contents are a stop; no
repair, reinstall, predicate expansion or replay of a consumed operation is
included. The P421 file writer independently repeats clean-root admission.

The writer has no USB dependency. The later reader reuses the established
native USB transport; this is a separate boot after Android recovery, not a
new Android file-mounting capability. Each candidate requires its own live
binding and finite attended grant. H0 qualification grants no device effect.

## Fixed writer and proof limits

The new [file pilot policy](../operations/S22PLUS_DEBIAN_FILE_PILOT_V1.md)
specializes common boundaries 2 and 3 for this exact profile. Debian's
packaged shell stays initial PID1. Its fixed children perform the retained
73 platform plus eight UFS module preparation and a clean-only protected
checker/root admission. The checker is unprivileged and its exact child must
settle before RW; timeout/error never signals PID1's inherited process group.

After admission, the writer may clear only native_data's RAM RO flag, mount
ordinary ext4 with `nosuid,nodev,noexec,nodiscard`, conditionally create the
fixed root-owned `var/lib/lab` directory, and exclusively create one root-owned
mode-0600 `s22-evidence-<run>` file of at most 16384 bytes. Exact ancestor
ownership, modes and device identity, no-follow traversal, one link and
`O_EXCL` protect existing files. No journal replayer or installed init is
packaged in P421. Other partitions receive no writer.

The authenticated file contains actual parent/boot/source measurements, the
complete bounded RAM preparation log, and eight chained records for the fixed
pilot. Writes and file/parent synchronization are checked. New persistent-phase
RO-clear, mount, directory and file effects require kernel BOOTTIME below
300 seconds; cleanup remains separate. Short writes or sync failures stop
further records without retry. The last record is `UNMOUNT_NEXT`. A complete
file therefore proves pre-unmount history, not successful unmount, later
filesystem cleanliness, installed Debian services or USB access.

The host's 360-second window starts at the original N transfer completion.
It performs no device observation and produces only
`AWAITING_OFFLINE_FILE_RECORD`, with device activity unknown. Physical Download
and one original A follow within the finite grant. Blocking kernel calls may
outlive userspace deadlines; this route claims no automatic recovery or
quiescent device. Android recovery restores boot and health, not previous
native_data contents. A file cannot capture failure before storage admission.

The H0 collector requires both original-A closures, exact target/A equality,
one consumed N/A pair per operation, distinct writer/reader run identities,
and the reader's sealed writer selection. It rederives raw transfer and health
evidence and binds registry consumption to each image and operation. It saves
the acquisition and raw file before strict decoding. A valid prefix remains
partial; malformed or missing bytes never establish non-execution or permit
the writer to run again. Later reader cleanliness and Android health remain
separate facts.

## Validation and retained provenance

Final physical A/B packages and all 12 final ARM64 cases passed. The suite
runs the actual Debian initramfs/file writer and then
a separate actual mountless reader boot on private regular VM disks. Only
virtual board/module discovery differs. No Samsung device is contacted.

The cases cover normal complete retrieval, dirty root, wrong UUID, existing
record, module insertion failure, missing RAM evidence, short write, file
sync failure, parent sync failure, unmount failure, expired write start and
checker timeout. Outside-native_data bytes must remain unchanged in every
case. Rejected pre-write cases must leave the complete disk unchanged. Partial
I/O cases preserve raw later-reader bytes and retain failed writer status;
even a complete pre-unmount file cannot promote failed unmount to success.

The unchanged default journal helper separately passed all six actual ARM64
cases: replay, clean skip, pre-existing orphan, orphan introduced by replay,
corrupt journal and checker rejection. Focused host validation passed 110
distinct tests across file protocol/window/consumption, early/USB compatibility, sealed
reader, strict recovery, V3 sessions, protected-root admission and boundaries.
All 21 touched Python files compile. The shared measurement extraction leaves
the actual P419 ARM64 observer byte-identical. Four mutations of actual
qualified artifacts were rejected: a virtual physical build, an injected
physical fault, a foreign VM run and an I/O failure promoted to success.
The collector rederived actual consumed P419 and P415 closures with process
and raw-command acquisition blocked and journals unchanged.

The scoped HEAD-plus-change export passed all 99 portable tests. Its attempt
to load the additional handoff-boundary module stopped because that historical
import requires the intentionally absent private P328 key; the 11 tests in
that module had passed in the complete working closure. That import failure
is retained, with no key copied or validation weakened. Boundary and diff
checks passed.

| Qualified image | Image receipt SHA-256 | AP bytes |
| --- | --- | ---: |
| P420 | `e18552d2695ecbd2cc97c8713c03cc24943084c664a734a5f1832e08b70d39c6` | 33853481 |
| P421 | `b2a713115d19c8e4dc36094f846352eb0e6e6041e032d2f3c4a81f189c066f5f` | 35532841 |
| P422 | `222e447a93ced4a8a8bd7fdf4933ba0acb50f04a14cf76494de1820cee187c8f` | 32276521 |

P421's 8544203-byte A/B initramfs has SHA-256
`da4ef0b38d84be62a8a439f1e6b8baff6cd1b8e730506881b8c9819f28b169d0`.
Its final build receipt is
`6707618e27e5749f3a58410f8b86e51e909db7f83df12c9239a5385775af7b1c`;
the 12-case final VM receipt is
`aa13305afe39f171784f8e909b1338ba1f2de1a1098339087a20eac6835b1255`.
The frozen host closure has 109 paths and the separately reviewed offline
collector closure has 70; the collector is not a device-execution gate.
The file build/VM snapshots contain 168/195 inputs. P420/P422 runtime
closures contain 168/165 inputs.

Private inputs and all raw evidence are retained under
`workspace/private/outputs/s22plus-debian-file-evidence-h0-20261012-1/`.
The final builds, VM receipts and frozen host/consumer snapshots identify the
exact bytes used. Independent `/root/review_debian_early_h0` returned PASS_GO
for all three capabilities, the collector and scoped common/target amendments,
with no unresolved findings. Its own actual A/B/AP audit, all 12 file-route
and six journal raw VM rederivations, source joins and negative qualification
checks passed. The three current capability tips bind those reviewed bytes;
previous recovery/reader tips were saved byte-for-byte before publication.
Existing consumed P415/P418/P419
artifacts and journals retain their original provenance. Directly required
sealed-reader catalog/build/VM plumbing is included in this unit; unrelated
S20+ and Debian handoff work remains outside the scoped commit.
Qualified artifacts bind the complete frozen working-tree closures. The
scoped commit excludes inherited edits and never substitutes for those
retained build identities.

## Concrete readiness and next physical boundary

The completion criterion is met: all three images have concrete independently
validated task preparations. `connected-p420-1` performed only the existing
fixed Android D0 health/shell-v2/GPT/statfs transcript. Its 17 raw captures
rederive, both health brackets match the same original-A boot, and the exact
Android32 GPT/capacity and original boot/supporting digests pass. This does not
read native_data files or prove its consistency. No read failure occurred.
`offline-p421` and `offline-p422` validate without device reads; current health
and every live binding remain mandatory when those operations actually start.

`ready-audit.json` and `route-ready.json` retain the exact first task, later
task receipts, ordered prerequisites and collector invocation. Every grant
remains unopened and no F1 owner exists. P420 may begin only under its fresh
returned attended 1800-second/one-operation grant. P421 needs P420's
`PROVED_CLEAN_ROOT` and healthy original-A closure plus its own fresh grant;
P422 needs the closed P421 owner and a separate grant. No automatic chain or
consumed-candidate replay is enabled.

Physical native_data consistency, persistent file survival and Samsung
initial-PID1 proof remain unclaimed until these separately authorized
operations produce the required evidence.
