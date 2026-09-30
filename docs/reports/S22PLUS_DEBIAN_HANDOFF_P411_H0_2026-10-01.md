# P411 Debian progress and same-gadget handoff: H0 qualification

Date: 2026-10-01 KST. Target: only `SM-S906N/g0q/S906NKSS7FYG8`.
Candidate: P411 `v0.4.0-rc.11`, archive-free handoff V2.

This report preserves the **historical H0 qualification snapshot**. The later
[physical attempt](S22PLUS_DEBIAN_HANDOFF_P411_FIRST_RUN_2026-10-01.md) rejected
native_data's journal-recovery flag before mounting or Debian execution and
closed healthy on original Android. P411 and its finite grant are now consumed;
the preparation statements below grant no replay or filesystem repair.

## Problem and selected correction

[P410](S22PLUS_DEBIAN_HANDOFF_P410_FIRST_RUN_2026-09-30.md) proved actual
installed Debian init as initial PID1, but did not establish NCM or SSH.
Its stock kernel dispatches configfs setup through the first gadget's global
pointer. Creating a second gadget after unbinding the first leaves that
dispatch blocked. The physical post-hook reach and reset cause remain unknown.

P411 retains the first `g1` object and configuration, and transfers their
ownership to Debian. Sequential SysVinit wait children now report installed
init, actual rcS and runlevel-2 completion, followed by thirteen authenticated
same-boot/init/cron/sshd samples spanning at least 120 seconds. They close ACM
before starting each original rc child, so services cannot inherit that
diagnostic descriptor. No native daemon or competing service manager remains.

After retaining the complete runtime proof, the host can send the one fixed
release. The Debian observer rechecks the RAM USB script's exact size/hash and
tmpfs identity, closes ACM, unbinds the exact UDC and verifies empty readback.
The fixed script removes only the known ACM configuration link, keeps `g1`
and its ACM function, creates NCM on that same object, binds once and configures
the declared local address. Failed checks park without a second transition.
The host stops if the same native endpoint returns after departure.

The common contract, selected target and V3 adopt the separate
[V2 policy](../operations/S22PLUS_DEBIAN_HANDOFF_V2.md). One compound intent and
the original 300-second deadline cover preparation through authenticated release
acceptance. Already-started services and an uncertain later USB operation can
remain active; this bound is not a shutdown or automatic-recovery guarantee.
The prospective operation remains attended, one operation/3600 seconds, one
fixed SSH shutdown and at most one physical original-A return. No package
workload, ordinary reboot, reinstall or additional partition access is selected.

## Admission after P410's writable lifetime

Healthy Android closure does not prove native_data clean. P411 rechecks the
exact storage/GPT/entry-41 identity, partition-only RAM RO, clean superblock,
complete unprivileged `e2fsck -fn`, installation markers and original witness
before clearing RO or executing any installed code.

All 8,969 archive entries remain exact except the policy's bounded wtmp data.
The only optional additions are individually checked startup logs, a 32-byte
random seed and the first boot count `1\n`. Mode, owner, link count, size,
root-device identity, symlink-free traversal and exact remaining tree count
are enforced. Unknown or malformed additions, changed immutable files, dirty
ext4 or incomplete checking stop before RW. There is no filesystem repair or
journal replay. The physical root's current admissibility remains unknown.

The old V1 catalog row is retained as historical data but cannot select the V2
builder. P410's policy, review, artifact and consumed journal are not repinned.

## Validation

The final normal ARM64 system-QEMU run uses actual retained SysVinit, rcS,
runlevel 2, cron and sshd on a regular-file native_data fixture containing the
allowed post-P410 startup data. Thirteen samples cover **120.042 seconds**.
Pinned SSH joins the same kernel boot; the fixed shutdown powers QEMU off,
leaves the exact expected boot count, clean ext4 and a successful read-only
checker result. Bytes outside native_data are unchanged.

The VM explicitly substitutes virtio/SLIRP for Samsung NCM. It establishes
userspace and protocol behavior, not electrical USB enumeration on Samsung.
The production shell script is separately executed against explicit
regular-file configfs substitutes: same-object success, already-bound refusal,
mid-transition failure and repeated-start rejection all pass.

Seven pre-RW negative fixtures cover dirty ext4, immutable mismatch, unknown
addition, wrong boot count, malformed wtmp, short seed and a mutable-path
symlink. Every case preserves the whole backing disk. Additional ARM64 cases
cover stale/damaged state, inherited descriptors, failed rcS, actual cron
termination, absent/bad START and release, failed UDC retirement and changed
RAM USB script. Failed or withheld continuation never acquires SSH; every
case preserves bytes outside native_data. An acknowledged release is not
mistaken for later UDC/script completion.

One negative VM initially exposed an H0 reader assumption: after abrupt
termination, an ordinary boot-count write can still be buffered or journaled.
The original raw evidence was retained. The reader now reports interrupted
count durability as unknown while preserving producer checks and isolation
checks. Exact count, clean ext4 and successful checking remain mandatory after
the positive controlled shutdown. No physical action was involved.

The selected real ARM64 validation contains **21 cases**, including the final
positive and twenty negatives. Earlier-phase cases reuse unchanged reached
code; the new final script check has its own final positive and changed-script
negative. All 21 raw RX streams rederive with the current strict consumer.
The final tests comprise **87 Debian tests and 72 related owner/root/transition
tests**. The latter initially found two old fixture requests without the
mandatory operation field; the fixture was corrected without weakening the
production owner. All touched Python compiles. Actual prepare/witness/hook
outputs are static ARM64 ELF, and their independent A/B builds match.

The actual P411 Image differs from P410 only in the declared identity spans.
All other bytes, including the independently reviewed stock dispatch slices,
are identical. This preserves the exact-Image analysis and its 16 host/ARM64
source-control-flow cases, including first-object rebind. These are separate
from physical USB proof.

Actual boot/AP A/B bytes match and the qualified archive contains only the
expected boot member and RAM assets. Artifact-byte validation passes.

| Artifact | SHA-256 |
| --- | --- |
| Kernel Image | `5e2d9f87dd86e2abb43084716a1b4eaec18d53d2c8fecdc0871c104bfa1836d4` |
| Boot image | `77295d80312446adb8be0bb99fe95b834a1d8869a85bb3378ffa04e1c773edad` |
| Boot-only AP | `a177361ac980beb8354f31ebc041c4ab64d4e97b94e49a2480e88604296713b5` |
| Qualified image record | `8126eb05c46a1baa5310c3f03311fc000ce6668a1e478b85318a7ba83c54df83` |
| Frozen source closure | `2750bb4d16e3b2dd41b2a62c9b7686f6de9d63cf2bdebc53b6cad8a3337a04e9` |
| Final validation record | `de46b6cb9181ce50ccba4a45c9202135a7d68adbdf1f19215dead3a7767a3ce8` |
| V2 capability review | `e2807aa5fb99fc08508330d02a768eb027ad432b31557b4e95976406d1e1c581` |
| Concrete offline task | `4dba33825c8cea17463266ac2e1e8b3591a45641ed68a2fb1caa5dc93f696aa9` |

The private bundle is
`workspace/private/outputs/s22plus-debian-handoff-p411-h0-20261001-1/`.
It retains raw VM/protocol/filesystem captures, failed H0 attempts, artifact
receipts and 261 frozen source files. Independent reviewer Helmholtz returned
**PASS_GO**, findings `[]`, bound to the source closure, qualified image and
final validation above. The reviewer independently verified the source/snapshot
identities, actual artifacts, 73 validation pins, 21 raw protocol/TX sequences
and 159 passing tests. This is capability qualification only.

## Concrete offline readiness

The actual task is **READY_H0_PRELIVE_ONLY**, selecting only `debian-handoff`,
one operation, 3600 seconds and attended original-A recovery. Its retained
target, rollback and demonstrated recovery identities are joined to the
qualified candidate without a new device read.

Offline preparation was executed with connected command production, Android
commands, lane capture/revalidation, native-host entry, USB observation, grant
opening and subprocess execution blocked. No blocked entrypoint was called.
The resulting task also passed actual static `validate_task(live=True)` policy
and artifact checks; that function does not itself observe a device.
`fresh_connected_health=false`, `current_root_admitted=false`,
`grant_opened=false` and `device_actions=0` remain explicit. The candidate is
unclaimed and no F1 owner is present.

## Physical boundary

This task performs **zero device actions**, including no connected D0, grant,
experimental transfer or control. A90 and S20+ are untouched. Offline
preparation can bind retained target, rollback and recovery evidence but cannot
establish fresh health or current root admission. Future execution must still
revalidate the exact lane, obtain fresh rooted Android health and pass current
native admission. A dirty root stops; this candidate cannot repair it.

P410 remains consumed and closed healthy. Its prior installed-init proof is
retained independently from P411's VM service liveness and prospective NCM/SSH.
Physical service liveness, NCM enumeration and SSH remain unproved by this H0
work. Package/service management and ordinary Debian reboot remain later units.
