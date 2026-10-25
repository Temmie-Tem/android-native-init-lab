# S22+ bounded packaged-cron workload and reboot persistence V1

Status: **REVIEW_GATED_CAPABILITY**. This specialization is only
`post-autoboot-p458-cron-v1`, namespace `p459`, `debian-autoboot-v1` and the
existing V3 `debian-autoboot` owner on `SM-S906N/g0q/S906NKSS7FYG8`.
Definition, H0 tests and review do not grant a device operation.

## Finite effect and unchanged recovery owner

The [bounded reboot specialization](S22PLUS_DEBIAN_REBOOT_V1.md) supplies one
fresh N, two admitted Debian boots, one ordinary reboot, four admitted
native_data RW lifetimes, one final shutdown and one original A. The attended
one-operation/3600-second grant, absolute 300000 ms BOOTTIME limit per boot,
360-second host windows and physical Download/original-A return remain.
Both complete protected admissions remain mandatory in each boot. No new
transfer, third startup, filesystem repair, installation or arbitrary command
is added. The old P458 image and grant remain consumed.

Only boot 1 adds packaged cron stop, start and restart, then one scheduled
fixed integrity-report workload. The report is one new exclusive 512-byte
native_data file. Boot 2 authenticates that file before each writable lifetime
and exposes its unchanged bytes through the existing bounded SSH evidence
operation. It does not run another workload or create another cron report.
Ordinary cron/PAM process-local operations and the existing bounded Debian
log producers retain their declared scope; no package configuration is changed.

An unexplained failure ends research. The original owner retains its exact A
and health/closure continuation, with no uncertain control or transfer retry.
Original-A health is not native_data rollback or final filesystem consistency.

## Service lifecycle and actual producer

The existing sequential Debian runlevel child waits for packaged rc2 to finish.
It then invokes only `/usr/sbin/service cron stop`, `start` and `restart`, once
each with bounded child waits under the original deadline. Script exit zero
does not establish lifecycle success: the old daemon must disappear, and each
new daemon must have the exact installed executable, root and distinct PID.
Process observations bind PID and `/proc` start time. The original 120-second
stable cron/sshd observation begins after the final restart; no restart occurs
inside that observation.

An initial readiness wait is at most five seconds. Each later wait shares its
sole service dispatch's ten-second deadline, clipped to the original boot
deadline. Only absent/empty root-owned pidfiles and disappearing process or FD
objects are eligible for read-only reobservation. Malformed nonempty pidfiles,
program/hash/root mismatches and forbidden descriptors stop immediately.
Pending/final samples retain their reason; a wait never repeats the service
command or begins the stable-service window before complete identity checks.

The installed cron package executes the fixed job. The producer accepts only
the selected boot-1 state and actual ancestry to the pinned restarted daemon,
allowing only the packaged cron and shell intermediate processes. It hashes
the exact installed cron and sshd programs, then records their identities with
the run, first-boot identity, early nonce, root device, sealed mount count,
hook identity, lifecycle observations and bounded BOOTTIME values.
Direct helper execution is not scheduled-work evidence.

The asynchronous job never appends the existing sequential runtime chain.
The sequential observer accepts completion only after the independent report,
successful synchronization/close receipt and disappearance of the winning job
and its recorded intermediate cron processes. It then emits the existing
service-complete record. File appearance alone is insufficient.

## Fixed RAM schedule and scratch storage

The installed `/etc/crontab` is still a read-only bind of the existing RAM
asset. Its initial exact bytes declare no jobs. After lifecycle success,
the fixed hook changes only that RAM source inode to the sealed schedule,
with empty `MAILTO`, fixed PATH/shell and one fixed command redirected to
`/dev/null`. The successful job consumes an exclusive RAM intent and changes
the same schedule inode back to the exact idle bytes before opening its disk
output. Both checked transitions have distinct whole-second mtimes; the system
clock is never changed. A failed transition never authorizes rearming.

Retirement is a cron reload, not cancellation of an already queued job.
One-shot ownership bounds output attempts, not the number of cron launches.
Already queued invocations seeing the original intent return without schedule
mutation, output creation or repair. They cannot repeat a partial write.
No report writer may begin a disk write after its original device deadline. Missing work is a
failed result; two minute ticks within 120 seconds are not assumed.

Failure, including deadline expiry, retains one separately owned RAM revocation
attempt. A trusted lifecycle owner or already-claimed worker consumes one
exclusive RAM revocation intent, truncates the exact READY inode first and then
the exact mounted crontab source inode to zero, sets that schedule inode's mtime
to zero so packaged cron discards its cached system table, and records the two outcomes in
that RAM intent. The original deadline never renews; only these fixed RAM
revocation/record operations may complete after expiry. No disk report is
created, removed, repaired or retried by cleanup. A later owner may read the
original result but cannot repeat the revocation. Missing READY is harmless;
an incomplete schedule is revoked without accepting its contents. A worker
which already accepted its intent may still be in flight; failed cleanup and
kernel activity remain uncertain and require the original physical A return.
This is not a guarantee of an empty cron queue or device quiescence.

The retained package opens its PAM session and temporary output file before
the fixed command's redirection. Its original PAM policy remains intact.
Before installed init, only the already-admitted `/tmp` directory is covered
with an 8 MiB/512-inode RAM tmpfs, mode 1777 and nosuid/nodev/noexec. No native
directory is created or changed by that mount. This bounds cron scratch
storage without permitting another persistent-data writer. Qualification
exercises the actual packaged PAM and temporary-file path.

## Report and exact persistence

The only new persistent path is `var/lib/lab/s22-cron-<run>`, regular root:root
0600, one link, the native_data device and exactly 512 bytes. It is absent at
both boot-1 admissions. A RAM intent is consumed before `O_EXCL` disk creation;
the producer checks file and parent synchronization and close, then publishes
its fixed RAM completion receipt. A partial file or absent completion is not
repaired, removed or retried by another scheduled invocation.

Both boot-2 admissions require the report. Its HMAC, first-boot early nonce,
hook/program identities, phase/count and lifecycle grammar must agree with
the authenticated first early/runtime pair. The host additionally requires
byte-for-byte equality with the original boot-1 acknowledged snapshot. The
full-tree checker still rejects undeclared files and metadata differences.
The schedule is reintroduced in RAM; this does not demonstrate persistent
configuration, package installation, DNS or a general-purpose Debian system.

The four final P458 early/runtime files are exact producer-derived expectations
from the original authenticated reboot/shutdown captures and healthy closure.
They are required by the new complete immutable table, with their exact bytes,
metadata and source provenance. They are not post-Android retrieval evidence;
the first successful current admission establishes that later retention.
Expected mount count after P458 is 22. A fresh fixed pre-build baseline must
measure the current clean state and count; unexpected state is investigated,
not automatically learned as permission to write. The existing reviewed
`debian-reboot-baseline-d0-v1` profile is reused without expanding its commands.

## Qualification and activation

Independent review covers common/target adoption, new RAM transitions and
scratch mount, lifecycle and producer ancestry, one-shot output/settlement,
both root consumers, exact SSH joins and the actual production qualification.
Qualification uses the real packaged cron and ARM64 producers/consumers across
two kernel boots. It preserves outside-native_data bytes and exercises missing,
changed, foreign, linked, wrong-mode, oversized and wrong-boot output, direct
invocation, incomplete attempts, failed lifecycle and deadline boundaries.
The cache-loaded failure case restores the active cached timestamp after
truncation, exercises the production zero-mtime revocation, and verifies no
second job entry for at least 65 seconds with the same packaged cron daemon.
Historical P458 consumers retain their original meaning and source provenance.

A new physical operation additionally requires current source-bound review,
a physical fixed baseline, exact current target/health/artifact binding, usable
attended Download recovery and a returned finite grant through the existing
owner. Synthetic H0 inputs cannot admit physical execution. No new RPC, generic
SSH command, automatic recovery guarantee or approval-waiver lane is created.
