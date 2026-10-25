# S22+ bounded persistent cron configuration V1

Status: **REVIEW_GATED_CAPABILITY**. This specialization is only
`post-autoboot-p459-cron-config-v1`, namespace `p460`, `debian-autoboot-v1` and
the existing V3 `debian-autoboot` owner on `SM-S906N/g0q/S906NKSS7FYG8`.
Definition, H0 qualification and independent review grant no device operation.

## Exact effect and owner

The [bounded reboot specialization](S22PLUS_DEBIAN_REBOOT_V1.md) supplies one
fresh N, two admitted Debian boots, four native_data writable lifetimes, one
ordinary reboot, one final shutdown and one physical original-A return. Both
complete protected admissions in each boot, the absolute 300000 ms BOOTTIME
deadline per boot, two 360-second host windows and the one-operation/3600-second
attended grant remain binding. There is no new transfer, third boot, repair,
package installation, general configuration editor or arbitrary command.

Only two new persistent files are selected: one exact cron.d configuration
created in boot 1, and one exclusive 512-byte integrity report created by the
packaged cron in boot 2. Successful boot 2 removes that exact configuration
once. It does not remove the report. The old P459 schedule, output, candidate,
grant and historical source bindings remain consumed and unchanged.

Failure does not guarantee removal. A partial or still-installed configuration
may remain on native_data. No failure, timeout or later health check authorizes
another creation, write, unlink, service dispatch or control. The original
attended owner retains only its existing physical A and final-health path.
Android health establishes neither native_data rollback nor final consistency.

## First boot: creation and no report

The fixed leaf is `etc/cron.d/s22-lab-<run>`, with the exact 32-hex run ID, no
dot in the leaf, root:root 0644 and one link. Both boot-1 admissions require it
and `var/lib/lab/s22-cron-config-<run>` to be absent. Its sealed text contains
the run comment, fixed shell/PATH, empty MAILTO and one minute job executing
only `/run/s22-debian/hook cron-job`, with output redirected to `/dev/null`.
The installed `/etc/crontab` remains the existing idle RAM overlay.

After packaged rc2, the sequential observer performs the reviewed cron stop,
start and restart lifecycle. It waits for the old daemon and all pinned cron
processes to settle after the initial stop. Then it creates the final cron.d
leaf directly with `O_EXCL`, writes its exact bounded bytes, checks file and
parent synchronization and close, and reopens it for full readback. There is
no temporary disk file, rename, overwrite or partial-file cleanup.

Authenticated sequential records bind its inode, size, nanosecond mtime/ctime
and creation BOOTTIME before the service window. Subsequent start/restart
dispatches and complete executable/root/PID/start-time readiness remain
one-shot and bounded. The existing 120-second cron/sshd window follows.

Any first-boot cron invocation returns before creating a RAM job intent or
disk report. Completion requires the configuration to retain its recorded
identity and all job intent, READY, completion and success markers to be
absent. This does not assert that cron dispatched no process or performed no
PAM activity. The original package's PAM behavior and existing bounded log
producers remain; temporary output is still confined to the reviewed
8 MiB/512-inode, mode-1777 RAM `/tmp`.

## Second boot: exact configuration consumption

Both protected admissions require the exact first early/runtime pair, its
completed reboot intent, and the same cron.d contents, inode, ownership, mode,
link count, size and nanosecond mtime/ctime. The new report must still be absent.
Unknown or partial files never become learned history. Current clean ext4,
sealed mount-count progression and the full immutable-root comparison remain
mandatory before either writable lifetime.

The packaged cron starts normally and reads the retained disk configuration.
After current-boot preparation and daemon identity checks, the sequential
observer creates one authenticated READY record in RAM. A scheduled worker
must join the actual second boot, early nonce, selected hook, native_data root,
original daemon PID/start time and permitted cron/shell ancestry. It verifies
the same configuration before claiming its exclusive RAM intent. Already
claimed or not-yet-ready invocations return without a disk write.

The worker hashes the pinned installed cron and sshd executables and writes
one root:root 0600, single-link, 512-byte report with `O_EXCL`. The report binds
both boot identities, first-boot configuration identity, current mount count,
workload identities and bounded times. File and parent synchronization and
close must succeed before the fixed RAM completion file is published.
Only after that completion file's checked write/fsync/close succeeds may the
worker publish one fixed empty mode-0700 RAM success directory. This final
atomic publication has no subsequent fallible worker operation. A readable
full-size completion file alone is insufficient.

The worker never appends the sequential runtime chain. The observer requires
the authenticated disk report, matching completion file, exact final RAM
success marker and disappearance of the recorded worker/intermediate
PID/start-time identities. A failure can revoke the RAM READY gate, but cannot
publish successful configuration consumption or retirement.

## Successful retirement and failure boundary

After the complete 120-second service window and settled successful worker,
normal retirement must acquire a **fresh** exclusive RAM revocation claim and
receive successful checked results for the gate revocation and its record.
A pre-existing worker-abort claim, even containing readable successful fields,
is not a normal-retirement authorization. Failed record synchronization or
close also stops retirement.

The observer stops the original daemon once and waits for its disappearance,
then performs a bounded census of all current-root pinned cron executables,
including orphaned PAM/intermediate cron processes. Two quiet samples are
required within the same service deadline. Vanished proc rows allow only a
bounded fresh read; other read errors reject the claim. Kernel threads and
zombies cannot continue this userspace execution. The previously recorded
winning job identities must already have settled.

The observer reopens and retains the exact configuration descriptor, rechecks
content and metadata, and rejects mounts covering `/etc`, `/etc/cron.d` or the
exact leaf, including same-filesystem binds. It unlinks the one selected name
once, checks parent synchronization, name absence and zero links on the held
inode, and closes its descriptors. Only then does it start cron once and
require full new-daemon readiness before the authenticated retirement and
service-complete records. The existing SSH health and shutdown helpers still
require a live pinned cron daemon. No reload timing assumption replaces this
stop/settlement/unlink/start sequence.

Failure or expiry permits only the separately owned fixed RAM READY revocation
and RAM outcome record. It does not unlink disk configuration, repair output,
dispatch a service command or retry any uncertain effect. A worker already in
flight may remain active; neither revocation nor an observer stop proves an
empty cron queue, device quiescence or automatic recovery.
These are permanent safety invariants of this exact capability. Changing
their effect, settlement, timing or recovery meaning requires independent
review; they are not temporary per-experiment approval gates.

## Evidence and qualification

The new runtime revision/domain and job domain distinguish this capability
from P458/P459. Boot-1 SSH evidence includes the authenticated creation records
and exact RAM copy read from the disk configuration. Boot 2 includes the same
configuration bytes, exact first pair, current job report and authenticated
retirement. The host reports preservation, consumption and retirement as
separate joined facts. A final native_data consistency claim still requires
separate post-return observation.

The four final P459 early/runtime files and its cron report enter as exact
authenticated final-producer expectations, with original provenance. They are
not post-Android retrieval or present-clean-state proof. Expected M is 26;
physical preparation must use the unchanged reviewed fixed baseline D0 and
reject any different current state. Synthetic H0 baselines cannot admit a
physical image.

Independent review covers these common/target boundary additions, actual C and
Python producers/consumers, process settlement, final publication, failure
behavior, exact unlink and owner integration. ARM64 qualification uses the
real installed cron/PAM and two kernel boots. Its first-root failure fixtures
come from the actual first kernel's completed ordinary-reboot exit, before a
fresh QEMU kernel; they never reconstruct configuration identity after deletion.
H0-only runtime substitutions share the same compiled virtual producer and
are selected by fixed VM kernel arguments, absent from physical execution.
Qualification includes changed/missing/linked/foreign/partial configuration,
wrong phase, invalid ancestry, completion and revocation failures, proc errors,
an orphaned cron process, deadline expiry and unlink synchronization failure.

A device operation additionally needs the current source-bound independent
review, physical baseline, qualified exact artifact, current target/health,
usable attended Download recovery and the existing returned finite grant.
No old record is repinned and no additional physical operation is authorized
by this H0 change.
