# S22+ fixed mountless native_data evidence V1

Status: **REVIEW_GATED_CAPABILITY**

This separate profile applies only to operator-owned
`SM-S906N/g0q/S906NKSS7FYG8`, the retained Android32 GPT and native_data entry 41.
It reads bounded historical records before another writable boot can rotate
or replace them. Common and target adoption, independent source-bound review,
qualified actual A/B artifacts, fresh exact Android health, usable physical
Download recovery and a returned finite attended grant are all required.
The definition and H0 preparation confer no device effect.

## One fixed observation and original-A return

The existing V3 owner accepts only `root-evidence`: one operation within at most
1800 original BOOTTIME seconds. It performs exact fresh Android health, one
Download request and measured departure, one globally unconsumed reader N
boot-only transfer, authenticated native health and one fixed reader EXEC,
DETACH and descriptor close, same-boot native health/CONTROL and measured
Download departure, one original-A transfer, and full rooted Android32/GPT/
statfs final health. No E, bootstrap, N admission/reuse, prior tail, reconnect,
HUD, second reader invocation or other operation is permitted.

The partition-only RAM RO control has an exclusive durable intent before the
EXEC; the intent binds the command, run, nonce, boot identity and sequence.
Uncertain execution never repeats. Existing global F1 exclusion, same-host-boot
recovery, exact original-A artifact and endpoint checks remain binding.
Unavailable native CONTROL requires attended physical Download. After proved
A transfer only health/report continuation is allowed. An Android return does
not establish native_data cleanliness or restore overwritten historical data.
All consumed installation, repair and candidate claims remain consumed.

## Mountless read boundary

The helper reuses the root-inspector's exact UFS ancestry, full GPT, kernel
partition mapping, UUID/features and partition-only
`BLKROSET=1` plus BLKROGET/sysfs readback. LU0 access remains confined to the
sealed initial/final GPT metadata blocks. It never clears partition RO or
opens a writable partition descriptor. This protection is permanent.

A separate pre-admission callback bypasses the mount path for both clean and
validly identified dirty filesystems. No ext4 mount, journal replay, filesystem
repair, installed-code execution, chroot, archive extraction, GPT mutation,
userdata access or data write is authorized. The existing root-inspector's
clean-only mount prerequisite and digest-only tree observation are unchanged.
A mismatched identity, unsupported features or bad superblock checksum stops
before file decoding. Dirty/RECOVER/orphan state is preserved and reported. This reader does not
inspect the installed witness or admit the installed root for execution.

Only a static library reader runs as uid/gid 65534 with supplementary groups
and capabilities removed, no-new-privileges, parent-death handling and existing
child limits/settlement. Its sole storage descriptor is native_data fd 3 opened
O_RDONLY; the setup descriptor closes before parsing. ARM64 seccomp permits
partition reads only through pread64 on fd 3, output writes only to 1/2 and
fixed memory/time/process-exit support. It permits no open, ioctl, mount,
filesystem mutation or new descriptor. The custom libext2fs I/O manager checks
partition offsets and enforces 64 MiB/16,384 read-call limits; all write/resize/
discard/zero callbacks fail. The pinned e2fsprogs 1.47.2 library input is part of
qualification; no formatter or checker executable is packaged.

The sealed path table is the only file selection. Ancestors must be root-owned
directories without group/other write access; lookup follows no symlinks.
Selected files require the declared type, uid/gid/mode, one link and no deletion
time. Directory/inode checksums remain enabled; each used group descriptor is
checksum-verified before its inode-table location is trusted. Each row reports full-file
SHA-256 and size plus only the following bounded suffix where authorized:

| Fixed relative path | Maximum file bytes | Raw bytes |
| --- | ---: | ---: |
| `var/lib/lab/boot-count` | 32 | 32 |
| `var/log/wtmp` | 65,536 | final 1,200 |
| `var/log/dmesg` | 1,048,576 | final 1,024 |
| `var/log/messages` | 133,248 | final 1,024 |
| `var/log/messages.0` through `.2` | 133,248 each | final 512 each |
| `var/log/dmesg.0` and `.1.gz` through `.4.gz` | 1,048,576 each | none; digest/metadata only |
| Optional `var/lib/lab/s22-evidence-<run>` | 16,384 | entire file |

The optional run is one 32-character lowercase hexadecimal identity sealed at
build time; it cannot be selected by the host command. P415 does not select it.
This read definition grants no writer or local receipt creation. File status
is READ, ABSENT_IN_HOME_VIEW, READ_ERROR, METADATA_REJECTED or OVERSIZE; a failed
file emits no raw bytes or successful digest. Raw contents and identifiers
remain under `workspace/private/` and must never enter tracked reports.

The binary child result is bounded to 24,576 bytes, encoded within at most
65,536 command-output bytes. The inherited 240-second command deadline fits
one 300-second observation and the unchanged grant. Full child exit/settlement,
exact output framing, unchanged superblock/GPT and retained partition RO are
required. No file capture may trigger an extra invocation. Timeout, truncated
output, inconsistent accounting, unproved cleanup or transport uncertainty
is NO_PROOF and retains the existing recovery owner.

## Meaning and qualification

A completed acquisition is `PASS_ROOT_EVIDENCE_OBSERVED`. It establishes only
the read-only capture and the indicated view of those files. libext2fs reads
checkpointed home blocks without replaying JBD2. Committed journal-only inode,
directory or data updates may be absent, older or inconsistent in that view;
missing records never prove non-execution, including when a path lookup says
absent. Individual read/checksum failures remain explicit. A service log or
counter alone cannot prove the authenticated PID1, same-boot SSH or clean
shutdown claims of a different run.

H0 uses actual A/B ARM64 helper and full-image comparison, package-member and
source closure audits. Writable private regular-file VM disks exercise clean,
dirty, committed-journal-only, missing, symlink, hardlink, oversize, directory/
inode/group-descriptor-checksum, wrong-UUID and wrong-GPT cases. Whole allocated disk evidence
must remain byte-identical. Parser negatives reject partial or contradictory
records. VM board discovery is explicitly substituted; ARM64 Linux proof does
not establish Samsung hardware behavior.

The named foreground D0 preparation may reuse only root-inspection's fixed
original-A root-health brackets, shell-v2, full GPT and Android32 statfs reads,
including bounded pure-read reobservation. Offline preparation may use retained
target/recovery bindings but claims no fresh health; execution repeats complete
fresh checks. Neither preparation opens a grant, changes mode, mounts or reads
native_data, or transfers an image. The dedicated capability record is
`s22plus_native_root_evidence_v1_review.json`; older reviews and retained
artifacts preserve their original source identities.
