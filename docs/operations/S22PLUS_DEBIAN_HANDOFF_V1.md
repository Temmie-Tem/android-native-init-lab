# S22+ native-first installed-Debian handoff V1

Status: **REVIEW_GATED_CAPABILITY**

This separately reviewed scope selects only operator-owned
`SM-S906N/g0q/S906NKSS7FYG8`, the unchanged Android32 GPT, native_data entry 41
and the exact completed P401 root admitted by P409's checker/comparison.
P409 is closed and consumed; its successful readonly transition grants no
writable continuation. This policy implements the next unit of the
[handoff plan](../plans/S22PLUS_DEBIAN_HANDOFF_EXECUTION_PLAN_2026-09-30.md).

## One finite attended operation

Only V3 operation `debian-handoff`, one fresh archive-free N and one returned
attended grant are selected. The grant contains one operation and 3600 original
BOOTTIME seconds. It grants the following fixed sequence:

```text
exact rooted original-A health -> Android Download -> one fresh boot-only N
  -> authenticated first-boot native health -> protected exact root admission
  -> one native_data RW activation -> actual host-PID1 switch_root/RAM witness
  -> installed /sbin/init -> authenticated first-sysinit PID1 proof
  -> native ACM retirement -> Debian NCM and pinned SSH health
  -> one fixed SSH shutdown -> attended physical Download
  -> one original-A boot transfer -> full rooted Android32/GPT final health
```

There is no N admission, E, previous tail, optional reconnect, HUD, generic
EXEC, caller-selected init/argument, ordinary reboot, package workload or
installation. Older candidates, source pins, installation claims, journals
and grants retain their original meaning. H0 qualification and this adoption
open no grant or live effect. The foreground preparation may reuse the fixed
Android D0 profile in the readonly predecessor; a host-only preparation must
say that fresh connected health/binding remain for the live preflight.

## Exact writable exception

This specializes common boundaries 2 and 3 only for ordinary filesystem writes
by the admitted installed Debian userspace to native_data. It permits one
partition-only RAM `BLKROSET=0` and a normal writable ext4 mount after the full
P409 protected admission. There is no whole-disk RO control, formatter, repair,
raw block-data writer, partition-table change, extraction/reinstallation,
Android-data access or write to any other partition.

The real native PID1 retires the three native workers and proves ECHILD and no
other userspace before its checker. Exact UFS/LU0/GPT/entry-41 binding,
partition `BLKROSET=1` with ioctl/sysfs readback, clean superblock, unprivileged
static `e2fsck -fn`, complete retained archive metadata/content, start/complete
markers and filesystem witness all precede writable activation. Recheck GPT,
superblock and RO after admission. Dirty, mismatched or ambiguous roots stop.

Close every inspector descriptor, ordinarily unmount the `ro,noload` root and
prove that partition unmounted. Clear only its exact partition RO flag once,
verify ioctl/sysfs readback and mount anew as
`ext4,rw,errors=remount-ro,nodiscard`. Do not remount a `noload` mount writable.
Every failure after this boundary parks without cleanup retry, replay or
fall-through into the readonly inspector. The original compound intent owns
possible writes beginning at this activation, before any post-exec proof.

Debian's pinned startup/services may make their ordinary root, boot-count,
log and shutdown-receipt writes. These do not authorize another boot or
successor experiment. A forced physical return may leave native_data dirty;
healthy Android proves device recovery, not clean ext4 or preservation of all
Debian writes. Subsequent native_data repair, reinstallation or revised root
admission requires its own scoped work and authority.

## PID1, RAM preparation and USB ownership

Reuse the reviewed actual-parent terminal dispatch and fixed BusyBox 1.37.0
switch_root machinery. The same sealed run/nonce/current-boot state and one
300-second native deadline pass through worker retirement, admission, mount
moves and the separately executed static RAM witness. The witness now proves
the writable ext4 root and partition RO cleared, with ECHILD, no other
userspace, exact RAM executable and mount identity, and only fd0–3 remaining.
This is a distinct B profile; the readonly A profile still accepts only RO.

Before installed init, resize the moved `/run` tmpfs to at most 32 MiB/4096
inodes, nosuid/nodev, mode 0755. Provide private devpts and bounded `/dev/shm`.
Remove inherited RAM block aliases except exactly
`/dev/.s22-ext4-v1/native`; the retained mdev rule suppresses other block nodes.
Only read-only RAM file bind overlays add the first synchronous sysinit hook
to `/etc/inittab` and reduce the forced SSH command to `health`/`shutdown`.
No persistent init or package file is replaced. VM-only network overlays and
fault paths are excluded from the physical helper/image qualification.

Mark ACM fd3 close-on-exec, close all higher descriptors and exec the pinned
installed `/sbin/init`. The actual retained SysVinit closes only standard
descriptors itself, so its behavior is not used as native-fd retirement proof.
The first synchronous sysinit child precedes every rcS service. It reads a
0400 RAM state record with run/nonce/boot/deadline and HMAC, reopens only the
same ACM device with exact rdev and verified raw tty mode, and checks the
actual `/proc/1/exe` inode/hash and root. PID1 must retain neither ACM nor
state descriptors. Initial PID-namespace absence is checked on this kernel.

A failed hook parks permanently, including after a failed unbind. Exiting
nonzero is insufficient because SysVinit would continue to later sysinit
entries. No hidden native service manager survives. The host explicitly sets
and reads back CLOCAL for the deliberate device close/reopen interval.

## Fixed protocol and evidence

One durable compound intent precedes native request 37/sequence 5. It owns
all native preparation, the sole RW activation, the witness, installed init
and native gadget retirement. There is no renewed budget or authority at an
internal continuation. The idle fixed health EXEC/STATUS and accepted terminal
request use the existing native domain; later records use the separate
authenticated root-transition domain with original run/nonce/type/sequence.

The host retains the writable post-exec witness before request 39/sequence 6
and its ACK 171. It retains the installed-PID1 proof 172 before request
40/sequence 7 and its ACK 173. Before either request, no-clobber continuation
evidence joins the original compound intent and the exact prior proof. The
release additionally binds a fresh USB departure snapshot and original
30-second departure deadline. Partial writes, stale messages and missing ACKs
never permit retransmission or a new native connection.

After accepting release, the hook closes its ACM descriptor, verifies g1 is
bound to `a600000.dwc3`, writes the fixed unbind and reads back the empty UDC.
Only then may it exit and permit Debian rcS to configure the retained NCM
gadget. ACM release acceptance is separate from measured departure, NCM
arrival and SSH health. A lost ACK can leave Debian active with host proof
incomplete; it selects original recovery, never another release.

The host selects NCM by the retained physical topology, descriptor identity,
serial and exact host MAC. A fresh task-specific, nonpersistent NetworkManager
connection is bound to that interface/MAC, with the retained point-to-point
IPv4 addresses, no default route and IPv6 disabled. No gateway, DNS, forwarding
or general remote command is configured. The existing private client key and
known-host key are pinned; SSH uses strict host checking and a fixed source
address. Successful health must join both the current candidate marker and
the original native kernel boot digest. The forced command also checks actual
PID1/root, services and the only allowed block node. A banner alone is no proof.
Host connection cleanup rechecks only the task's recorded UUID, name, MAC and
interface before deletion. It runs after normal departure and on stop/recovery;
failure is retained as host cleanup evidence and never blocks original-A recovery.

Only one fixed `shutdown` SSH request is permitted, after health, with its
own durable intent. The retained shutdown script consumes its exclusive
receipt before invoking SysV shutdown. The host preserves producer status,
exact acceptance and measured NCM departure. Neither acceptance nor departure
is reported as proof that physical ext4 was cleanly unmounted.

## Return, stops and no replay

After shutdown/departure, normal execution pauses for attended physical
Download. Its original continuation window is at most 600 seconds within the
unchanged grant. The resumed transfer requires machine-proved exact Download
arrival and the existing Odin ticket/revalidation; no extra human statement
is needed for a fact those observers establish. The original A bytes and
demonstrated recovery remain bound throughout. No P399 or automatic native
return image is part of this scope.

An uncertain effect or transport stops research and retains the owner for
attended original-A recovery. An expired normal window allows only the
preauthorized recovery, never renewal of native/SSH work. One A transfer is
the maximum across normal and recovery paths. Completed A with failed final
reads selects health-only continuation; uncertain A never retransfers. H0
repair may rederive retained records without opening a device or executing
another transition. Authenticated PID1 prefix evidence remains distinct from
SSH success, operation closure and Android health.

## Qualification

Require independent review of common/target adoption and the complete changed
native/host execution closure. Actual A/B boot bytes must be identical and
contain the exact helpers, comparison table and RAM overlays, with no archive,
formatter or virtual substitution. Reuse unchanged P409 retirement/root-move
evidence and retained P401 userspace inputs with their original provenance.

Real ARM64 system-QEMU must run the installed SysVinit, first-sysinit hook,
pinned SSH health and shutdown against writable regular-file backing. Check
no writes outside native_data and distinguish virtual ext4 shutdown proof
from physical-device proof. Negatives cover admission failures, bad/stale
state, inherited native descriptors, missing/invalid release and failed UDC
retirement preventing rcS/SSH. Host tests cover damaged/partial/stale framing,
same-boot SSH, scope rejection, intent ordering and original-A health-only
recovery. Physical ACM/NCM and Samsung driver behavior remain live questions.

The temporary split between P409's readonly unit and this writable unit has
served its shared-retirement/root-proof qualification purpose. This profile's
fixed first-sysinit barrier addresses loss of PID1 evidence before USB changes;
revisit it only when a separately reviewed installed observer can prove the
same run/boot/PID1 facts without that interval. Changes to init, descriptors,
mounts, privilege, storage scope, transport or recovery trigger review.
