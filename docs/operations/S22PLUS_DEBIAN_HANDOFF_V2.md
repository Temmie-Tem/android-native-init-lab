# S22+ installed-Debian progress and same-gadget handoff V2

Status: **REVIEW_GATED_CAPABILITY**. H0 preparation opens no device grant.
Only `SM-S906N/g0q/S906NKSS7FYG8`, Android32 and native_data entry 41 are
selected. The consumed [V1](S22PLUS_DEBIAN_HANDOFF_V1.md) and P410 records
retain their original identities and meaning. The V2 runtime profile is
`thermal-v3-reconnect-ufs-drain-debian-handoff-v2`.

## One operation and its recovery

Reuse V3 `debian-handoff`, one fresh archive-free N, one finite attended grant,
one operation and 3600 original BOOTTIME seconds. Fresh exact rooted original-A
health, the verified original A and usable physical Download recovery precede
the sole N transfer. There is no device preparation implicit in H0 readiness.

```text
original-A health -> Download -> one N -> authenticated native health
  -> worker retirement and protected current-root admission
  -> one partition RO clear and normal native_data RW mount
  -> actual PID1 switch_root / RAM witness -> installed init proof
  -> fixed service-start continuation -> actual rcS -> actual runlevel 2
  -> 120 seconds of same-boot Debian/init/cron/sshd observation
  -> fixed release -> unbind and reconfigure the same first g1 as NCM
  -> pinned same-boot SSH health -> one fixed SSH shutdown
  -> attended physical Download -> one original A -> Android32/GPT health
```

The original compound intent owns writable activation, init, service start
and USB transition. Internal continuations never renew its deadline or
authorize another attempt. The native helper, witness and all Debian wait
hooks share the original 300-second deadline through authenticated release
acceptance, including the 120-second observation. Insufficient time parks
before USB release. Already-started Debian services and an uncertain
post-release USB operation may remain active; this deadline does not claim
to stop them. Such failure selects the bound physical original-A recovery.
The original host observation and grant bounds also remain enforced.

The one-A maximum applies across normal and recovery paths. Normal physical
return has at most 600 seconds within the original grant. Uncertain effects
stop research for the already bound attended original-A recovery; no partial
handoff, release, shutdown or transfer is repeated. Proved A with incomplete
health permits only health continuation. Android closure and Debian ext4
cleanliness remain different claims. There is no automatic recovery claim.

## Current-root admission after P410

P410 admitted the pristine installed root, then had one writable lifetime and
forced return. Neither its earlier comparison nor healthy Android proves the
current root clean. V2 always re-establishes exact UFS/LU0/GPT/entry-41 identity,
partition-only RAM RO with ioctl/sysfs readback, clean superblock with no
journal-recovery/orphan state, complete unprivileged `e2fsck -fn`, installation
markers and filesystem witness before any write or installed code execution.

Every retained archive path, type, mode, owner, symlink and regular-file hash
remains exact except the explicitly declared wtmp data below. The complete
tree must contain only those archive entries, the original three markers and
empty lost+found, and the following individually validated optional paths.
No broad `/etc`, `/var` or historical boot-critical-only exception is used.

| Data path | Mode / UID:GID | Bound |
| --- | --- | --- |
| `var/log/wtmp` | 0664 / 0:43 | Required original file; 0..65536 bytes, multiple of 400 |
| `var/log/dmesg` | 0640 / 0:4 | Optional, at most 1048576 bytes |
| `var/log/messages`, `.0`, `.1`, `.2` | 0644 / 0:0 | Optional, at most 133248 bytes each |
| `var/lib/urandom/random-seed` | 0600 / 0:0 | Optional, exactly 32 bytes |
| `var/lib/lab` | 0755 / 0:0 | Optional directory, link count 2, only the next row permitted |
| `var/lib/lab/boot-count` | 0644 / 0:0 | Optional, exactly `1\n` |

Regular files must have one link and remain on the exact root device.
Descriptor-relative traversal follows no symlink. Every optional path is
checked individually; exact remaining entry accounting rejects unknown
additions. The original P401 archive comparison is not rewritten, and allowed
mutable data is not described as byte-identical to that archive.

These paths and bounds follow the exact installed startup scripts, retained
VM mutations and reviewed producer behavior. They are admission bounds, not
assertions that any possible log output is bounded by them. P410 sent no
workload, reboot or shutdown command, so their receipts are forbidden. A
missing original entry, changed immutable content, unknown addition, bad
metadata, partial count, dirty filesystem or incomplete checker stops before
RO clear. There is no repair, journal replay, reinstall or allowance for a
second consumed writable boot.

After admission, close inspection descriptors, ordinarily unmount `ro,noload`,
prove the partition unmounted, clear only entry-41 RAM RO once, verify readback
and mount freshly as `ext4,rw,errors=remount-ro,nodiscard`. No writable remount
of a `noload` mount or other-partition access is admitted. Ordinary installed
Debian writes remain confined to native_data.

## Debian owns sequential observation and USB

Reuse the reviewed native-worker settlement, mount moves, writable RAM witness,
bounded `/run`, devpts, `/dev/shm` and block-alias pruning. Only the exact native
block node remains. Fixed read-only RAM overlays select the new inittab wait
entries, defer the installed USB script, empty the system crontab, and restrict
the forced SSH command to `health` and `shutdown`. Installed files are not
replaced persistently. Immutable cron.d/spool inputs remain checked; periodic
package work is not selected by this observation.

The first synchronous sysinit hook independently proves the actual installed
`/proc/1/exe`, root, current boot and absence of inherited native ACM/state
descriptors. After a fixed authenticated START it closes ACM and exits. It
does not hold rcS behind the 120-second wait.

Fresh helpers declare **observer revision 4** in their pinned result and image
selection. A missing revision means the retained revision-2 protocol only;
selection and helper revision must agree. Existing consumed artifacts and
replay projections retain their original meaning.

Revision 4 retains revision-3 wire framing and adds the following prospective
local-record specialization. Its changed closure requires independent review;
neither this document nor that review activates a candidate or supplies a grant.
The synchronous init hook creates exactly one root-owned 0600 single-link file
`/var/lib/lab/s22-evidence-<sealed-run-id>` on the admitted native_data root,
using exclusive creation and descriptor-relative no-symlink traversal. The
optional parent `var/lib/lab` is 0755 root-owned on the same device. It never
overwrites, removes, repairs or reuses an existing record file. These are
post-admission runtime writes only: the pre-RW tree and mutable-data bounds
above remain unchanged and do not admit historical record files implicitly.

The authenticated 256-byte header binds the qualified run, actual kernel boot,
nonce, original deadline, root device and init/hook hashes. Up to 120 chained
128-byte records bound total storage to 15,616 bytes. Header and parent sync
precede init proof; a checked START append precedes START ACK. Each append
revalidates the whole chain and inode/metadata, writes once, checks file sync
and readback, then closes its descriptors before child execution. Directory
creation/sync, short writes, sync, identity or close failures park without
retry. Check the original deadline immediately before each new mutation or
child creation; already-admitted writes may finish sync/close after expiry,
but this is not authority for another record, report, child or USB operation.

Only after a valid authenticated START is durably recorded may a known USB
reporting I/O loss cease to block the already-authorized fixed rcS/rc2 and
120-second observation. Each optional send is capped at 500 milliseconds and
the original remaining deadline. Only ENOENT/EIO/ENODEV/ENXIO on the expected
open, or EIO/ENODEV/ENXIO/EPIPE/ECONNRESET/ETIMEDOUT on the matching expected
send, qualifies. Endpoint, termios, close, authentication, child, service,
local-record or deadline failures still park. Before continuing, append and
sync REPORT_LOST with the exact phase/operation/sequence, then close the
original descriptor once. This authenticated chain is the shared disabled
state: all subsequent hooks load it before opening ACM, and never reopen,
send, read RELEASE or alter the gadget after report loss. They record the
remaining authorized facts and COMPLETE, then park. Already-started services
may remain active until the separately bound attended physical return; local
completion neither triggers recovery nor proves SSH or clean shutdown.

Records distinguish verified facts from intent: fork is not exec proof,
child exit is raw reaped status, and skipped reopen is not verified ACM.
Local RELEASE means an authenticated request was received, not that its ACK
or gadget transition succeeded. Retrieval uses only a separately selected
sealed bounded reader operation. Authenticated historical prefixes remain
partial evidence after a torn tail; missing records are not non-execution
proof, and neither records nor later reads authorize replay or retire the
original recovery owner. Local history, host receipt and external access
are separate claims.

The next Debian-owned wait child emits rcS entry and an authenticated
before-close boundary. It closes ACM, saves the close-return time, then reopens
and verifies the exact ACM endpoint and actual installed init before emitting
the reopen boundary. Only then does it fork the original rcS. The finite parent
keeps ACM while waiting; before exec, the child performs `close_range(3, UINT_MAX,
0)` and checks fd 3 is absent. No executed service inherits ACM or state fds.
The runlevel-2 wait child similarly opens and verifies ACM before forking the
original rc 2. The deferred lab-usb entry performs no gadget change.

Authenticated boundary records distinguish before-close, verified reopen,
child-forked, ten-second waiting heartbeats and the exact reaped child's raw
wait status. Child-forked is not exec proof. Close-return timing becomes visible
only after successful reopen and transmission; its absence cannot identify
which operation failed. Both phases share the original 300-second deadline
and a forty-record consumer cap, with separate ordered sequences and same-boot
identity. Only zero child exit permits completion progress. Failed wait hooks
park rather than return a failure that SysVinit could ignore. Timeout attempts
to kill the direct child but does not claim all descendants stopped.

The host retains raw bytes first, then bounded frame receipt metadata with
host CLOCK_BOOTTIME, frame digest and captured-prefix length. These are receive
upper bounds, not device execution timestamps; buffered frames may share a
prefix length. No clock conversion to kernel printk timestamps is implied.
This finite diagnostic addresses P413's unobserved close/startup interval;
reassess its necessity after the first closed physical revision-3 result.
Changed timing/descriptor lifetime means a successful successor would not
retrospectively establish the cause of P413's USB departure.

After rc2, the same fixed observer verifies actual init/boot/root and the
pinned installed cron and sshd processes. It sends thirteen authenticated
samples spanning at least 120 seconds under the original deadline. Reopened
ACM writers are sequential and have distinct fixed record sequences. RAM
exclusive stage markers reject duplicate invocation. There is no background
native manager, generic shell, respawn, arbitrary executable or new command
vocabulary. The 120-second interval addresses the P410 post-init/native-return
incident; reassess this diagnostic interval after the first closed physical
V2 result and retire it when equivalent Debian-owned progress evidence exists.

On the still-connected path, only after the host durably retains the complete runtime proof can its fixed
release request be transmitted. Before accepting release, the observer
rechecks the fixed RAM USB script's generated size and SHA-256. It closes ACM, unbinds the exact
original `g1` and checks empty UDC. A fixed RAM script reconfigures that same
object and its existing configuration as NCM. It removes only the known ACM
configuration link; it never deletes g1 or creates a second gadget. Alias
identity, original descriptors, expected link, absent NCM function and empty
UDC precede mutation. Failure parks without retry. This corrects the exact
stock kernel's first-object global dispatch and avoids its stale-pointer
delete/recreate hazard.

Host release acceptance, actual UDC completion, ACM departure, NCM arrival and
SSH remain separate evidence. Release ACK still precedes disconnection and
cannot prove the entire later script. The existing exact topology/descriptor/
MAC selection and task-specific nonpersistent local network remain unchanged;
there is no default route, DNS, forwarding or general remote command. Pinned
SSH health must join the same candidate and kernel boot. A native endpoint
return is a failed transition, never authority for reconnect or replay.

## Qualification and success claims

Require independent source-bound review of this common/target adoption and
the changed native, host, root-admission and USB closure. Build and inspect
the actual identical A/B boot bytes, static ARM64 helpers, generated headers
and RAM assets. Physical packages must reject VM/fault substitutions.

Run the actual installed SysVinit/rcS/rc2, 120-second observer and SSH/shutdown
in ARM64 system-QEMU. Bound the virtual network substitution explicitly; it
does not qualify Samsung electrical USB behavior. Reuse exact-Image dispatch
analysis and execute representative first-gadget rebind control-flow checks.
Exercise the fixed adoption script's expected state and failure behavior.

Negative coverage includes dirty/mismatched roots, malformed allowed data and
unknown paths, stale state, inherited descriptors, failed startup/service,
short or malformed liveness, absent/bad continuations and failed USB retirement.
Revision 3 also exercises failure between close and reopen, script nonzero exit, exec failure,
signal termination, inherited-fd rejection and the original startup timeout.
Partial boundary evidence must never authorize release or reconnect.
Revision 4 also exercises pre-START loss, post-START ACK/boundary/progress/open
loss, storage short-write/sync failures, endpoint/close faults and deadline
expiry. Actual ARM64 execution must show complete bounded local service proof
after qualified report loss, no later ACM open/send/release, and no SSH access;
critical failures must park. Compare authenticated local records with raw wire
prefixes, and preserve interrupted VM files before recovering a private copy.
Pre-RW failures must preserve the entire regular-file fixture; all VM cases
must preserve bytes outside native_data. Check real consumer framing, partial
raw rederivation, intent order and no-replay recovery. Reuse unchanged P409
proof only within its original scope and preserve all P410 frozen evidence.

Report installed-init proof, rcS/services progress, finite runtime liveness,
NCM, SSH, shutdown, filesystem state and Android return separately. A partial
successful prefix survives a later failure without becoming full-boot PASS.
Host-only READY means the implementation and artifact are qualified; it does
not claim fresh connected health or current native_data admission.

## Post-loss boot identity assessment

The existing native D0 profile requires a completed admitted baseline, no
unresolved F1 owner and the same boot with increasing observation ordinals.
It cannot be reused to identify a new boot after handoff loss. Current native
AUTH emits boot identity and immediately enters return preparation, so simply
closing the host after identity is not a read-only branch. Revision 3 adds no
post-loss connection or new command.

A future preparation-free, identity-only receiver would need separate review
for both native and Debian endpoint lifetimes while retaining the failure's
original recovery owner, no-replay rule and finite budgets. It could report
**changed authenticated boot**, **same authenticated boot**, or **no authenticated
identity**. Timeout, USB re-enumeration and descriptor equality alone cannot
choose between reboot and gadget reset. This assessment grants no such action.
