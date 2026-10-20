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
Prospective catalog data may carry `evidence_run` only for this reader profile;
the declaration, generated helper, complete image and image selection must all
bind the same value. Omitting it preserves the original fixed P415 selection.
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

### Sealed automatic-boot pair

The separately qualified `autoboot-pair` selection replaces the entire table
above with exactly two files for one sealed run: `var/lib/lab/s22-early-<run>`
(16,384 bytes maximum, whole file) and `var/lib/lab/s22-evidence-<run>`
(15,616 bytes maximum, whole file). Both require root-owned regular 0600
single-link metadata. No historical log rows accompany this selection.
The catalog's fixed `evidence_selection` value requires `evidence_run`; no
caller path or filename prefix is accepted. The declaration, generated helper,
packaged bytes and image binding must agree on this exact selection.

For this pair only, the binary output bound is 32,256 bytes: 64 framing bytes,
two 96-byte rows and at most 32,000 file bytes. The parent command-output cap
remains 65,536 bytes, including hexadecimal encoding and all protocol lines.
The generated selection supplies both child and supervisor limits. Actual
producer/consumer qualification must cover both files at their maxima, the
full outer framing and independent oversize results. Default and historical
selections retain their 24,576-byte bound and original path table.

Acquisition remains separate from interpretation. The H0 collector preserves
both raw files before decoding, authenticates the selected writer's physical
run/key/source identities and retains valid partial record chains. When both
headers are available it checks their kernel boot and derived nonce join.
A runtime-only authenticated header may report its own boot, nonce and root
device; these remain local producer observations, not an independent external
boot or transition witness. It cannot establish SSH or a clean shutdown.
Missing or older home-block records do not erase another file's valid prefix
and never prove non-execution. The collector performs no device acquisition,
mount, repair or journal replay and never changes the consumed writer terminal.

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
native_data, or transfers an image. The current prospective P447 reader selects
the dedicated capability record `s22plus_native_root_evidence_p447_review.json`.
The earlier `s22plus_native_root_evidence_v1_review.json`, consumed P427 review
`s22plus_native_root_evidence_p427_review.json`, consumed P429 review
`s22plus_native_root_evidence_p429_review.json`, consumed P431 review
`s22plus_native_root_evidence_p431_review.json`, consumed P433 review
`s22plus_native_root_evidence_p433_review.json`, consumed P436 review
`s22plus_native_root_evidence_p436_review.json`, consumed P438 review
`s22plus_native_root_evidence_p438_review.json`, consumed P440 review
`s22plus_native_root_evidence_p440_review.json`, consumed P442 review
`s22plus_native_root_evidence_p442_review.json`, consumed P444 review
`s22plus_native_root_evidence_p444_review.json`, and all retained
artifacts preserve their original source identities; this selection does not
repin an old review or renew a consumed reader. Only the new reviewed pair
selects the two-file table and its declared binary bound. P440 seals the same
pair for the closed P437 automatic writer after P439's closed strict replay,
retaining the same sizes, metadata, mountless read and original-A return.
It adds no path class, replay, write or installed-root admission. P438's dirty
pre-replay capture and P439's negative complete-root comparison remain unchanged.
The later read may observe newly checkpointed bytes; it cannot identify the
three unaccounted entries from their count alone, prove second-boot effects
without authenticated records, or turn missing home-block files into
non-execution evidence.

P442 seals exactly the early/runtime pair for the closed P441 automatic writer.
Its Android closure and retained-stage records do not establish current
native_data consistency or complete home-block file visibility. The reader
retains the same metadata, byte limits, partition-only RO and mountless
semantics, with no journal replay, repair, writer, installed execution or root
admission. The new identity/path data require fresh artifact qualification;
the unchanged reader machinery retains its reviewed semantics. P440 and P441
remain consumed. Any later recovery or history-table admission is separate.

P444 selects the same exact P441 pair after P443's closed strict replay.
Path selection, metadata, sizes, partition RO and mountless read semantics
are unchanged. P442's dirty capture remains original evidence. P443's clean
superblock/checker result and negative complete-root comparison do not prove
these files' present contents or identify its unaccounted tree paths. This
fresh reader makes no repair, replay, filesystem write or root admission.

P447 seals exactly the early/runtime pair for the closed P445 automatic writer.
The writer's healthy Android closure and retained early-cleanup/second-admission
start records leave current native_data consistency and later execution
unknown. This prospective reader changes only its identity and sealed writer
run. It retains the same two paths, metadata rules, whole-file byte limits,
partition-only RO and mountless semantics. It adds no replay, repair, write,
installed execution or current-root admission. Authentication uses the actual
P445 writer artifacts; missing home-block records never prove non-execution.
Later recovery and writable-history admission require their separate scopes.
