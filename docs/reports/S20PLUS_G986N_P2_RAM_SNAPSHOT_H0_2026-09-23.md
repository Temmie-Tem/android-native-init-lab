# S20+ P2: early PID1 RAM snapshot

Date: 2026-09-23. Target: `SM-G986N / y2q / y2qksx / G986NKSS8IYC2`.
Status: **CONSUMED — NO_PROOF — BOOT ROLLBACK AND FINAL TWRP HEALTH COMPLETE**.

The separately approved live transaction closed at **2026-09-23 04:15:44 KST**
as `NO_PROOF_NATIVE_PID1_RETURNED_TWRP_HEALTHY`. Candidate and rollback boot
transfers each completed once. The fixed acquisition returned a shell execution
error instead of a snapshot frame. Automatic Download entry was uncertain;
attended physical Download entry, the fixed boot rollback and a fresh healthy
retained-T2 return completed. The shared guard is released. Neither the candidate
nor its acquisition, control or rollback may be replayed.

P2 implements the [selected observation route](S20PLUS_G986N_PID1_ROUTE_SELECTION_H0_2026-09-23.md):
capture the kernel log prefix through the first PID1 witness into RAM before
restoring and executing the existing Magisk init, then retrieve that snapshot
through ADB on the same boot. A fresh private boot-only candidate was built.
The P2 profile is connected to the complete shared TWRP F1 runtime.

The initial host implementation and validation unit completed with device
commands, transfers, reboots, activation and consumption all **zero**. The
subsequent preparation and approved live transaction are recorded below with
separate counters.
P0/P1 consumed artifacts and journals are unchanged. A90 and S22+ device
commands are zero. The work establishes no live PID1 or dynamic-snapshot
relocation proof.

## Implemented behavior

The [freestanding producer and reader](../../workspace/public/src/native-init/s20plus_p2_pid1_ram_snapshot.c)
share one [format and limits declaration](../../workspace/public/src/native-init/s20plus_p2_ram_snapshot_contract.h).
The producer's first syscall checks PID 1. It captures raw, contiguous kmsg
records from sequence zero through its own witness, including boot and PID
namespace identity. It uses only the existing RAM root and `overlay.d/sbin`;
directory traversal rejects symlinks and checks actual RAM filesystem types.
There is no persistent-file fallback or new USB configuration.

Capture is bounded to 2 MiB, 8,192 records and one second. A separate one-second
publication budget allows bounded failure diagnostics to survive capture expiry.
An exclusive mode-0600 `.part` file is written, fsynced, read back and compared,
then published with a no-replace rename. Diagnostic and incomplete snapshots
remain distinguishable from a successful publication. Magisk is restored to
`/init` and executed with the original argv/envp; a failed restore or exec parks
without attempting another image or repeating the witness.

The separate static reader admits only its fixed executable locations in
`/debug_ramdisk` or `/sbin`. It checks the snapshot's RAM filesystem, regular-file
type, owner, mode, link count, bounded extent and stable metadata, and compares
boot IDs before and after reading. It preserves bounded partial bytes in its
framed output. It performs no filesystem writes. Output is nonblocking with a
five-second deadline; kernel syscalls themselves are not forcibly preemptible.

The [collector](../../workspace/public/src/scripts/revalidation/s20plus_g986n_p2_snapshot_observer.py)
stores exact stdout, stderr and acquisition status before interpreting them.
It checks target, topology, build, boot, SELinux, root identity and the reader
artifact. Android UI completion is a diagnostic field, not an acquisition
prerequisite. Only target absence/offline state and a missing reader can be
retried, within 60 attempts and a 180-second observation budget. A failed `su`,
failed Magisk path lookup, unexpected identity, acquisition fault or malformed
result stops collection. This is not a general delayed-root retry mechanism.

The [codec](../../workspace/public/src/scripts/revalidation/s20plus_g986n_p2_ram_snapshot.py)
uses a new acquisition type, `pre-exec-ram-kmsg-v1`. It retains the existing
sequence-zero, continuity, kernel/init-dispatch, first-userspace-record, PID,
namespace and boot checks. A missing prefix, overrun, malformed frame, changed
file or diagnostic status cannot produce `MATCH`.

The [P2 owner](../../workspace/public/src/scripts/revalidation/s20plus_g986n_p2_ram_snapshot_f1.py)
joins that structural result to the proved candidate transfer, exact artifacts,
source closure and leased acquisition. It rederives saved evidence from the raw
files during validation. The shared kmsg parser is explicitly source-bound;
loaded observer, codec and parser functions are also checked for rebinding.

The owner uses existing target-session locking, consumed-candidate registration,
process-cage supervision, boot rollback and attended TWRP return machinery.
Rollback identity uses the fixed root identity script without depending on
snapshot/reader availability. A reporting cut never repeats collection or the
candidate transfer. Healthy TWRP alone cannot close an unproved boot rollback.

## Candidate and validation

The [builder](../../workspace/public/src/scripts/revalidation/build_s20plus_g986n_p2_ram_snapshot_h0.py)
verifies the existing handoff transformation, adds only the fixed reader under
`overlay.d/sbin`, and checks that snapshot filenames are absent from the image.
Kernel, DTB, boot header and all unrelated ramdisk entries are preserved. Two
independent materializations produced identical output hashes. Private outputs
are under `workspace/private/outputs/s20plus_g986n/p2_ram_snapshot_v1/`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Producer ELF | 4,296 | `549be09f9231cacfde6d2cc5a2e2ac66e21c72edc130ac7b5609674fe6af239b` |
| Reader ELF | 3,184 | `183dd1600b5f4ecb00899f398011f0e1722a97cd40db70d3772ea1205e45ec79` |
| Boot image | 67,108,864 | `0e6198b0fc02e5c726ff6b7a5bfab82f83d49d85302dfd273a1f2e9918e3d629` |
| Boot-only AP | 25,845,801 | `8a3e1d95d9b4d01c4637b3d20f89547f2042122a5cecceba81a8f5d0a7d5d650` |

Validation completed:

- ARM64 cross-compilation and ELF inspection; exact retained target UAPI review
  for syscall numbers, flags and structures; representative real ARM64 file
  syscalls under QEMU, including short writes and failed readback.
- Twelve [producer/reader tests](../../tests/test_s20plus_g986n_p2_ram_snapshot.py),
  with multiple failure cases per test: real tmpfs file operations, exclusive
  creation, publication/readback faults, log gaps, metadata changes, partial
  reader output and failed init restoration.
- Ten [integration tests](../../tests/test_s20plus_g986n_p2_integration.py): actual
  installed engine, session flock, fixed-command admission, raw capture/replay,
  transfer/evidence join, readiness, failure/reporting cuts, and terminal behavior.
- Twenty-five existing shared-runtime regression tests, Python compilation and
  full P2 host-closure validation.
- Independent review: **PASS_GO_H0**, no remaining findings, covering the core,
  collector, owner integration and shared-runtime changes. Review identities and
  validation receipts are retained privately under `p2_ram_snapshot_h0/`.

The production C is used through a syscall seam in the fault harness. PID 1,
procfs/kmsg, root ownership and Magisk relocation are modeled; tmpfs file I/O is
real. The integration tests replace hardware receipts and intercept process
creation before ADB; host Python processes supply fixture bytes. These tests
do not simulate a complete Samsung boot or execute Magisk's Android boot path.

The retained-T2 baseline's prospective qualification was refreshed for common
Contract Revision 29 after independent reviews of the Revision 28 and 29
S22-specific common-contract changes. Its implementation
changed only the prospective record path/comment. Both the original consumed
qualification and Revision 27/28 qualifications remain intact. This refresh grants
no connected qualification or new device action.

## Remaining live boundary

The follow-up below implemented and reviewed the P2 target amendment and
mechanical activation check. At preparation, `P2_F1_ACTIVE` was true and the exact
immutable capability record validated. Candidate execution required its separate
fresh prepared approval; capability activation granted no candidate transfer.

Magisk 30.7 source supports the selected overlay relocation route; the actual
S20+ boot must still establish that the dynamic snapshot reaches the reader.
A resident root can modify the RAM file, so this is not hostile-root attestation.
Early syscall or handoff failure may leave no USB; automatic recovery is not
claimed. A future run must retain its attended physical recovery conditions and
prove boot rollback plus fresh TWRP health before closure.


## Execution preparation follow-up

The operator requested completion through readiness and confirmed physical
attendance. The existing exact TWRP boot-identity D0 completed with
`PROVED_S20PLUS_G986N_TWRP_BOOT_IDENTITY_METADATA`: seven commands, five selected
S20+ reads, zero foreign-target commands, and zero writes/reboots/transfers.
It establishes current retained-T2 recovery health and boot metadata, not
candidate proof or a boot-content read.

The new [P2 target section](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-p2-ram-snapshot-attended-f1)
provides the reviewed activation and preparation scope. One immutable capability
record binds exact dormant/active owner bytes, critical source and authority
identities, fixed artifacts and the fresh 900-second prepared-approval rule.
The only mechanical source edit was `P2_F1_ACTIVE = False` to `True`.
It does not import P0/P1 activation records or approvals.

Initial activation review returned **PASS_GO**, zero findings, for activation identity
`18df2943e71be21c09680d757800fe164ac1d39dd3b7b2f2bfe43a85c309edd4`.
Initially reviewed active owner SHA-256:
`63070ffebc518369cc40594c7649108ba444ec0b5161f662b63f86c7906d5f39`.
Private activation record SHA-256:
`d6717008128a78b8e542d5b98bf89cb92d6cd0d3263a00cdeecb3656f0b44ff7`.
The request, reviewed source copies and focused logs are retained under
`workspace/private/outputs/s20plus_g986n/p2_activation_v1/`.

Six activation tests and twelve integration tests passed. They cover exact
activation bytes, source/authority drift, malformed record types, duplicate keys,
symlinks/hardlinks/modes, missing approval, and recovery readback without
build-only development files. The C header remains a required runtime input
because the Python codec reads its declaration. Historical build provenance is
compared with both the fixed owner declarations and the prepared binding.
The unchanged candidate/core and shared-runtime tests are reused.

The completed preparation below collected fresh qualified TWRP health,
performed one journaled Download entry and returned the exact approval. No
candidate or rollback payload is authorized by this preparation request.


### Pre-control preparation stop and corrected binding

The first preparation retained one clean ADB inventory and then stopped with a
host `P0F1Error` before any selected command, control intent, prepared binding,
claim or transfer. Its guard was released by the existing engine. The actual
retained TWRP row advertises `model:SAMSUNG_y2q` / `product:twrp_y2q`; the shared
lease binder incorrectly recognized only Android's model tag. Thus the next
read was rejected for an unbound serial. This is not a failed TWRP identity or
a candidate execution. The original run and activation-v1 bytes remain intact.

A host regression using the real recovery metadata reproduced the same failure.
The corrected runtime provides separate private TWRP and Android binder aliases.
TWRP uses the owning run's validated retained predecessor and existing exact
recovery-row selector. Both aliases preserve the same no-serial-switch invariant;
the P2 Android observer uses the unchanged Android predicate. No device identity
or TWRP health requirement was removed.

Independent review returned **PASS_GO**, zero findings, for the corrected
activation identity
`de40bd11cc8b40209b1fb9695ab2cc86321174e942c2c13924acfd56d7fd48bc`.
Active owner SHA-256 used for preparation and execution:
`76de1a7c6d2a68249df27ab8aa816291b971a5e1686cb5cf991b89c929b9509c`.
The matching immutable `activation-v2.json` SHA-256 is
`428e42d8c2bf0e0abdbdce79b0e7db7a4551d2d907c2ed712f5b9313dd62ee7d`.
All 44 focused tests pass before and after activation, including real TWRP
metadata, fixed environment, invalid recovery rows and forbidden serial switches.
The engine, C/header and candidate artifacts remain unchanged. Incident receipts,
source copies and logs are under `workspace/private/outputs/s20plus_g986n/p2_activation_v2/`.

The target's reviewed effect-scoped clarification permits a fresh preparation
under the same attended request: the previous host rejection consumed zero
control budget. Fresh TWRP health and a new journal are still required. No
control, candidate or rollback operation from the old run can replay.


### Completed preparation before the exact approval

The corrected preparation completed successfully. Fresh retained-T2 health was
collected through the real leased runtime, the single `adb reboot download`
result was proved dispatched, and exact Download arrival was bound. The owner
then validated the prepared record through its real consumer. At this stage the
device awaited approval in Download mode; candidate and rollback transfers were 0/0.
The source run is `run-1790103602144341728`; its private prepared record and
approval remain in the P2 run root. The approval expiry was
**2026-09-23 04:15:10 KST** and cannot be renewed by editing that record.

This completed the requested preparation scope. Candidate execution and required
boot rollback/TWRP final health then followed under the exact approval below.
No S22+, A90 or other-target selected command was issued by this preparation.

## Approved live transaction and closure

The operator returned the exact prepared approval while it was valid and remained
available for physical recovery. The private source run is
`workspace/private/runs/s20plus-g986n-p2-ram-snapshot-f1/run-1790103602144341728/`.
Its original append-only journal and raw captures are preserved. All times below
are KST on September 23, 2026, derived from those journal records.

| Time | Recorded transition or result |
| --- | --- |
| 04:04:45 | Exact approval durably accepted. |
| 04:04:50–04:04:52 | One candidate boot transfer; `odin_transfer_completed`, host-process quiescence proved. |
| 04:05:37 | Same-boot Android/root/reader identity qualified; acquisition classified `NO_PROOF`. |
| 04:05:38 | One rollback Download-entry command returned 1; durable outcome `uncertain`, never resent. |
| 04:12:01–04:13:51 | Physical rollback armed; machine observer confirmed the exact Download arrival. |
| 04:13:55–04:13:56 | One fixed resident-Magisk boot rollback; `odin_transfer_completed`, host-process quiescence proved. |
| 04:15:44 | Operator's TWRP return followed by fresh fixed health validation, terminal publication and guard release. |

### Acquisition result and its limits

Observation readiness selected attempt 21 (zero based). The reader existed at
`/debug_ramdisk/s20plus_p2_snapshot_reader` both before and after acquisition:
3,184 bytes, SHA-256
`183dd1600b5f4ecb00899f398011f0e1722a97cd40db70d3772ea1205e45ec79`.
Both checks passed root, exact target, reader artifact and RAM-filesystem checks
on the same boot. Android `boot_completed` was still empty, as expressly allowed
for observation; full Android health was not established.

The one snapshot capture returned **90 stdout bytes, zero stderr bytes, host exit
0, and 148 ms elapsed**, with no timeout, overflow or capture-producer fault.
The stdout was a shell execution error treating the reader invocation as
inaccessible or missing; it was not the reader's required 160-byte frame header.
The codec correctly returned `NO_PROOF / reader-extent`. Raw stdout SHA-256:
`f04a646e6e91bbae432162132e3b73c313e408baf2d8992fa08bb4c6c376e04d`.
Exit 0 does not establish reader execution or snapshot semantics.

The retained observer source prequotes the entire `exec <reader>` argument on
the `adb exec-out su -c` path. Together with the shell error and successful
reader metadata checks, this makes command framing the leading H0 diagnosis.
This closure does not claim a completed causal reproduction. Static reader
presence is established; dynamic snapshot publication, relocation, content and
PID1 proof remain unknown. No acquisition or candidate retry was performed,
and no consumed image, source binding or journal was repaired in place.

### Recovery and final state

The fixed rollback identity recheck qualified the same Android boot before the
single Download-entry command. That command returned 1 with a private
device-not-found error, and bounded observation did not establish Download
arrival. Its original uncertain outcome remains unchanged. Physical recovery
used the existing preauthorized fallback. An initial physical-arm invocation
reported an unavailable session lease before creating physical-intent nodes;
the later arm succeeded. No cause is asserted for that transient host rejection,
and no control or payload was repeated.

After physical Download arrival, the fixed boot rollback completed once without
automatic reboot. The operator entered retained T2, and seven fixed final-health
captures qualified a fresh exact TWRP boot. Both `rollback_outcome_proved` and
`twrp_recovery_healthy` are true; the original owner published
`NO_PROOF_NATIVE_PID1_RETURNED_TWRP_HEALTHY` and released its owned shared guard.
This proves the journaled boot restoration and healthy TWRP return. It does not
claim a post-rollback Android boot, boot-content readback or automatic recovery.

Final counts are candidate/rollback **1/1**, recovery-partition reads/writes/
transfers **0/0/0**, and other-target selected commands **0**. The global consumed
claim remains; capability activation does not make this transaction reusable.

### Retained provenance and reporting validation

The private close record is
`workspace/private/outputs/s20plus_g986n/p2_live_close_2026-09-23/close.json`,
SHA-256 `073d52b8eb3bcd7597ccfb905523a1c5362d1d9f6a1b694217a208c1284a4b6d`.
It binds all 1,019 original run files and retains 30 matching source files,
including the exact consumed owner, observer, codec, engine and runtime.
The original run bytes were checked unchanged. The prepared record retains the
run's original authority hashes; later common-contract development drift was
recorded separately rather than attributed to the consumed execution.

The earlier H0 checks apply only to their reviewed scope. The live failure shows
that the fixture transport tests did not establish successful reader command
framing on the actual ADB/su path. Any successor needs a separate correction and
appropriate representative validation; this report grants no new effect.
This closure changed only the report and goal, with content/link, private-data
boundary and whitespace checks. No image rebuild, new device experiment,
commit or push was performed during closure.
