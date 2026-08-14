# A90 Headless Native-Wi-Fi / Isolated-Debian Design

Date: 2026-08-14
Selected target: Samsung Galaxy A90 5G only
Tier: H0 architecture and feasibility boundary
Status: selected direction; independent H0 review required; no live authority

## Decision

The production successor will not reproduce the retired atomic Wi-Fi ownership
diagnostic. It will keep the already-required native Wi-Fi owner in the native
namespaces and launch Debian as PID 1 of separate PID, mount, IPC, UTS, and network
namespaces. A reviewed veth and forwarding boundary carries IP traffic between
them. Debian never shares native procfs or the native AF_UNIX namespace.

This changes the meaning of handoff. Native PID 1 does not call the current
in-place `switch_root` and disappear. It becomes a small headless safety
supervisor. One direct child becomes PID 1 of the isolated Debian namespace,
pivots to the read-only UFS root, detaches the complete old root, and execs
Debian init. Debian is the appliance/service PID 1 inside its own namespace;
the native parent retains only supervision, Wi-Fi, logging, cleanup, power, and
recovery duties.

No H26 ordinal, version, build string, manifest, enable/latch path, artifact,
qualification, approval, or command is allocated here. The installed H24
resident remains the exact starting resident; its consumed D1 is never replayed.

## Why this is smaller

The retired diagnostic had to reproduce H24's Binder/property/service-manager
tree, distinct Android UID/GID/capability identities, seccomp notification
brokers, process-wide capability accounting, one-shot signalling, durable
terminal retrieval, and a second recovery transaction merely to learn whether
Wi-Fi survived a stop. Independent review proved that each added exception
created another security boundary.

The selected design does not stop or transfer Wi-Fi ownership. It reuses the
native Wi-Fi outcome and moves the trust boundary around Debian instead:

- native Wi-Fi processes stay in the native PID, mount, IPC, UTS, and network
  namespaces;
- Debian sees a fresh procfs, minimal `/dev`, private mount tree, and a veth
  interface in a separate network namespace;
- native Binder, property-service, abstract AF_UNIX, process FDs, old root,
  userdata block devices, and Wi-Fi control interfaces are not nameable from
  Debian;
- the only post-exec cross-boundary data plane is IP through the reviewed veth
  policy. Two scalar bootstrap pipes, one control and one receipt, exist only
  before the final Debian exec and both close at that exec boundary; Debian inherits no private
  control, health, or log FD.

This keeps one small native supervisor instead of adding a general-purpose
security broker. The supervisor is production machinery and therefore remains
in the permanent execution-critical closure; HUD, ownership-test, and general
shell machinery do not.

## H16 and H24 reference baseline

The exact comparison baseline is
`A90_H16_H24_ISOLATED_DEBIAN_COMPARISON_BASELINE_2026-08-14.md`. H16 is the
first live direct-UFS mechanical handoff boundary: it reached `switch_root_exec` at
boot time 11,760 ms, but did not prove authenticated SSH, Debian PID 1,
automatic return, DRM/display, final Wi-Fi, or full server readiness. H24
directly extends the H16 manifest ancestry and is the exact installed resident,
but its consumed D1 stopped at the newly added persistent-HUD gate after UFS
and writable-set setup and before `switch_root`.

The successor carries forward H16's fresh same-session UFS identity,
read-only/no-replay mount, immutable content, bounded writable set, ordered
stage timing, rollback, and fallback classes. It also carries forward H24's
later boot-private authorization and the always-fresh tmpfs/no-native-devtmpfs
principle. It explicitly does not carry forward H24's optional `ttyGS0`,
global console node, or non-`newinstance` devpts details. It does not carry
forward H16/H24's in-place native-PID1 root
transition, shared PID/proc visibility for persistent native Wi-Fi tasks,
persistent HUD/display gate, or SD evidence/property-root dependencies.

H16's 11,760 ms stamp is a boot-relative mechanical boundary, not an
authenticated-server boot time. Future measurements must preserve comparable
boot-to-exec and intent-to-exec anchors, then separately measure network,
authenticated SSH, and service readiness. Matching H16 speed cannot substitute
for the new namespace, device, network, evidence, and recovery proofs.

## Absolute required functions

The production lane must retain all of these:

1. exact A90 target/profile binding and boot-only candidate/rollback transfer;
2. durable no-clobber launch intent, one-shot automatic handoff, and no replay;
3. read-only `noload` UFS root with an exact immutable content manifest;
4. bounded tmpfs writable paths needed by Debian services;
5. an exact consoleless read-only Debian `/dev` with no devpts/ptmx/tty,
   physical/native character node, block, userdata, DRM, native devtmpfs, or
   inherited directory handle;
6. final native Wi-Fi health and a bounded IP-only path to Debian;
7. authenticated SSH and the selected server workload inside Debian;
8. durable stage/failure logs and performance timestamps without SD;
9. deterministic cleanup and native fallback when Debian launch or service
   health fails;
10. exact physical Download/TWRP recovery and boot-only rollback;
11. `HEALTH_PENDING_PERSISTENT_DEBIAN` while Debian remains live, followed by
    attended return/recovery before final `RESIDENT_HEALTHY`;
12. zero S22+/S20+ contact and no transfer of their profiles or evidence.

## Namespace and process topology

Before launch, native PID 1 is the sole long-lived supervisor. It starts or
validates the exact native Wi-Fi service subtree and records its stable health,
process, namespace, FD, socket, and driver identities. Before durable intent it
also requires the exact cloning thread already be `SCHED_OTHER`, priority 0,
nice 0, with no RT/RR/DEADLINE or Android scheduler boost; mismatch is
zero-effect `NO_GO` and the native state is never changed to make it pass. It
preopens one exact manifest-bound static bootstrap executable, creates one
parent-to-child control pipe and one child-to-parent receipt pipe with
`pipe2(O_CLOEXEC)`, exact ends, and byte caps, then creates exactly one Debian
bootstrap child with
`CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWIPC | CLONE_NEWUTS | CLONE_NEWNET`.
The child is PID 1 of the new PID namespace. Its inherited-mm pre-exec branch
may only close FDs, clear `FD_CLOEXEC` on the exact control-read and receipt-
write ends for this one transition, and call one exact
`execveat(AT_EMPTY_PATH)` of the preopened static bootstrap; it may perform no
mount, network, key, root, mapping, allocation, output, or Debian operation.
The executable FD closes on exec. From the first instruction of the clean
bootstrap address space, it restores `FD_CLOEXEC` on both pipe ends, closes
every other FD, and blocks before any effect. It then emits one fixed
`CHILD_READY` frame binding the exec identity and exact two-FD set. The parent
verifies the same pidfd and exact `/proc/<pid>/exe`, fd/fdinfo, `maps`, and
`map_files` receipt before sending `SIGSTOP` through the ancestor-namespace
pidfd and proving the stopped event with
`waitid(P_PIDFD, ..., WSTOPPED)`. Missing temporary flag transition, exec,
re-armed close-on-exec bit, clean mapping proof, unique frame, or stop is
`RECOVERY_PARKED`; no resource or network setup has occurred.
The parent obtains the pidfd at creation and registers that child outside every
generic `waitpid(-1)` path. Only ownership-aware `waitid(P_PIDFD, ...)` may
observe or reap it; the general shell and command-boundary orphan reaper are
not compiled into the production supervisor.

The parent and child prove:

- the child PID namespace differs from native PID 1 and has no native task;
- the child mount namespace is recursively private;
- the child IPC namespace differs from the native Wi-Fi IPC namespace; its
  initial SysV IPC tables are empty, `/dev/mqueue` is not inherited or mounted,
  `/dev/shm` is absent, and the positive syscall policy permits no SysV IPC or
  POSIX-mqueue/shared-memory creation;
- the child UTS namespace differs from native; trusted bootstrap sets the fixed
  public hostname `a90-debian` and empty domain name, while exact before/after
  observations prove the native hostname and domain name never change;
- every inherited procfs, sysfs, devtmpfs, old-root, cwd, directory FD, and
  native PID-1 virtual mapping is inventoried before the clean bootstrap exec.
  At `CHILD_READY` and every later stop the parent requires the manifest-bound
  static bootstrap plus only its fixed private anonymous stack/heap/vdso/vvar
  classes; exact `maps`/`map_files` provenance rejects every inherited native
  anonymous secret, `MAP_SHARED` mapping, deleted or memfd mapping, native
  file/device mapping, unexpected executable, or writable-executable VMA.
  The digest and allowed bounded anonymous ranges remain stable through the
  three preparation barriers, and the complete old root, cwd, and directory
  handles are absent after pivot;
- the child network namespace differs from native Wi-Fi's network namespace;
- no native AF_UNIX socket or netlink control socket is visible in the child;
- no native/preexisting socket FD reaches the service identity; the sole
  bootstrap-created listener remains only in the distinct filtered key daemon,
  and the forced dispatcher receives only its exact bounded channel ends;
- no unexpected task exists in either the native Wi-Fi set or Debian subtree.

IPC namespace separation does not isolate kernel keyrings. Before clone,
native PID 1 observes only its already-directly-subscribed thread, process,
and session keyrings through named no-create
`KEYCTL_GET_KEYRING_ID(..., create=0)` plus non-mutating description/link reads.
It never resolves `KEY_SPEC_USER_KEYRING` or
`KEY_SPEC_USER_SESSION_KEYRING`, because those special lookups may instantiate
per-UID keyrings even with `create=0`. It never calls
`KEYCTL_GET_PERSISTENT`, because that operation is get-or-create even when it
does not link the result. The direct child must begin with no
thread or process keyring subscription. During trusted bootstrap it joins one
new anonymous empty session keyring, proves its serial differs from every
observed native serial, and proves that it contains no link or key. Any
inherited thread/process subscription, failed replacement, native serial
visibility, or nonempty child session is `NO_GO`; bootstrap never revokes,
links, or mutates a native keyring and never queries or creates a persistent
keyring.

The trusted child bootstrap mounts one procfs associated with its own PID
namespace with manifest-fixed `nosuid,nodev,noexec,hidepid=2` options and an
empty read-only synthetic tmpfs at `/sys`; mounting or binding native sysfs is
forbidden. A fresh private tmpfs supplies immutable empty file/directory masks.
Before exec, trusted bootstrap masks the complete `/proc/sys` tree,
`sysrq-trigger`, `keys`, `key-users`, `kcore`, `kallsyms`, `modules`, `cmdline`,
`interrupts`, `iomem`, `ioports`, `devices`, `diskstats`, `partitions`,
`slabinfo`, `vmallocinfo`, `zoneinfo`, `sched_debug`, `timer_list`, and every
other top-level entry outside one exact allowlist. The allowlist contains only
numeric tasks from the child PID namespace, `self`, `thread-self`, child-netns
`net`, child-IPC `sysvipc`, child-mount views, and the finite read-only scalar
files proved necessary by the consoleless PID-1/Dropbear/workload trace.

The bootstrap proves the child proc superblock differs from native procfs,
enumerates the exact top-level grammar after native boot is stable, permits
only the named `self`/`thread-self`/`net` symlinks with exact targets, rejects
every other symlink/type drift or an unknown entry, applies and rereads every
mask, remounts each mask and the child proc superblock read-only, and verifies
that writes to `/proc/sys/*`, `sysrq-trigger`, `oom_score_adj`, and representative
per-task/global writable nodes fail. Native module load/unload is forbidden
after this receipt, so the top-level registry cannot grow behind the masks.
The only permitted global proc facts are the exact read-only scalar allowlist;
they are evidence values, never native task, root, FD, namespace, device, or
control endpoints. Failure to freeze this view is `NO_GO`, not a writable proc
fallback. If the frozen rootfs needs another proc or sysfs value, a future
design must name an immutable scalar-copy/read-only allowlist with no symlink,
device, write operation, or kernel handle and receive separate review.

The child constructs a bounded fresh tmpfs at `/dev` with exact
`nosuid,noexec`, byte/inode caps, ownership, and mode. Its complete manifest
allowlist is `/dev/null` (1:3, 0666), `/dev/zero` (1:5, 0666), `/dev/full`
(1:7, 0666), and `/dev/urandom` (1:9, 0444). `/dev/random`, `/dev/console`
(5:1), `ttyGS0`, generic `tty`, `ptmx`, `pts`, `shm`, every block node, every
physical/native character node, and any copied native-devtmpfs entry are
forbidden. The separately versioned minimal
rootfs and service trace must be consoleless: no console/getty service and no
open of `/dev/console`, `ttyGS0`, or a generic tty. Trusted bootstrap starts a
fresh session with no controlling tty, proves `tty_nr=0`, opens the exact
private `/dev/null`, verifies its rdev and mount identity, and makes that same
open file description fd 0, 1, and 2 before exec.

No devpts is mounted and no PTY allocation is a product function. Dropbear is
configured to reject PTY requests and the attended proof always uses non-PTY
SSH. The post-pivot tree contains exactly the four listed nodes, with bounded
tmpfs bytes/inodes, ownership, modes, rdevs, link counts, and no extras or
submount. Before exec the bootstrap remounts `/dev` read-only and proves node
metadata cannot change. `CAP_DAC_OVERRIDE`, `CAP_DAC_READ_SEARCH`, `CAP_FOWNER`,
and `CAP_MKNOD` are absent, so the 0444 urandom node cannot be reopened for
write or changed; null/zero/full writes have no mutable kernel/device target.

Any native block path used to mount UFS exists only before pivot: the bootstrap
binds its exact device identity, performs the read-only `noload` mount, closes
the source FD, and later proves that neither the node, FD, nor old `/dev`
survives. It validates the immutable UFS content, writable tmpfs set, and
Debian init before pivot. It uses `pivot_root`, changes cwd to `/`, detaches and
removes the old root, closes every bootstrap FD, proves the exact post-pivot
root/mount/FD tree, drops bootstrap capabilities, and only then execs Debian
init. `chroot` alone is forbidden.

After the exact proc masks and final read-only remount are verified, the
bootstrap sets `PR_SET_NO_NEW_PRIVS` and installs one reviewed classic-seccomp
isolation filter on every supported ABI.
The filter returns `EPERM` for `keyctl`, `add_key`, `request_key`, `unshare`,
`setns`, `mknod`, and `mknodat`; denies `clone3` completely because classic BPF
cannot inspect its pointed-to flags safely; and permits legacy `clone` only
when an exact mask proves that no `CLONE_NEW*` bit or unknown service flag is
present. Fork compatibility is fixed by the minimal-rootfs service trace, not
by a broad clone allow.

After trusted bootstrap finishes its own mounts, the same filter denies the
complete supported post-bootstrap mount/root API corpus: `mount`, `umount2`,
`pivot_root`, `chroot`, `open_tree`, `move_mount`, `fsopen`, `fsconfig`,
`fsmount`, `fspick`, and `mount_setattr`. The UFS root remains `nodev`; the only
non-`nodev` device filesystem is the already-verified exact private `/dev`, and
the child has no path or FD to native devtmpfs. Therefore no later process can
create a user namespace, regain namespace-local capabilities, create or attach
a mount, or manufacture a native rdev path. A separate device-controller
claim is unnecessary only while all four proofs remain exact: inherited filter,
mount-API denial, node-creation denial, and the closed device tree. Any gap
requires a separately reviewed device controller or is `NO_GO`.

This is a static default-deny filter, not a notification broker. Architecture
mismatch kills the task; every supported ABI otherwise returns `EPERM` for an
unlisted syscall. The separately versioned rootfs manifest binds the complete
positive syscall/argument allowlist derived from the exact consoleless PID-1,
Dropbear, and workload trace. The preceding named denials are mandatory
assertions inside that default-deny policy, not an exhaustive blacklist. The
filter is inherited across exec and descendants and cannot be removed. Missing
ABI/syscall coverage, a filter-load or negative-probe failure, unexpected
clone flags, or any service dependency is `NO_GO`.

The same all-ABI filter closes socket creation by family, type, and protocol.
Direct `socket()` is allowed only for `AF_INET` `SOCK_STREAM` TCP or
`SOCK_DGRAM` UDP, with only the exact traced `CLOEXEC`/`NONBLOCK` flag variants.
The network rules remain the separate destination/port authority. A local
`socketpair()` may use only `AF_UNIX` with the exact traced type and flags; it
creates no pathname or abstract endpoint and both FDs remain inside the child.
`socket(AF_UNIX, ...)` itself is denied, so no filesystem or abstract Unix
socket namespace is created by Debian in the first proof.

Every other family/type/protocol and unknown value is denied, including
AF_QIPCRTR/QRTR, AF_NETLINK (including kobject uevent), AF_PACKET/raw, Bluetooth,
NFC, VSOCK, CAN, XDP, and key/control families. The compat `socketcall` entry is
denied completely because classic BPF cannot safely inspect its pointed
argument vector, and the minimal rootfs manifest contains only exact AArch64
ELFs/interpreters. Interface discovery needed by the workload uses the bounded
read-only child proc view; all network configuration occurs in trusted
bootstrap before the filter and release. Missing family constants, ABI
coverage, or positive exact-service socket trace is `NO_GO`.

The positive policy also denies namespace-external or global kernel-object
allocators that the exact service set does not need: `perf_event_open`, `bpf`,
`userfaultfd`, `io_uring_setup`, legacy AIO setup, inotify/fanotify setup,
POSIX-mqueue and SysV-IPC creation/use, keyring calls, module/kexec/syslog
control, and all untraced multiplexed ioctl/fcntl/prctl commands. `getrandom`
is allowed only with flags 0 or `GRND_NONBLOCK`; `GRND_RANDOM` is denied and
`/dev/random` is absent, so the child cannot consume the global blocking
entropy pool. User-generated signals are limited to an exact non-real-time
service set; queued-signal APIs and real-time signal sends are denied. The
service trace must prove these exclusions on the exact kernel/libc/rootfs.

The final execution envelope clears the inherited environment and rebuilds an
exact finite allowlist, empties supplementary groups, and uses two distinct
manifest-fixed nonzero identities unused by every native task and file. The
service UID/GID owns Debian PID 1, the fixed login account, the forced probe,
and the selected workload. A separate non-login SSH-key-daemon UID/GID owns
only the Dropbear listener/session engines and the server private-key tree.
Trusted bootstrap creates one bounded auth tmpfs at the manifest-fixed service
home `.ssh`, installs only the boot-private client public key as mode-0600
`authorized_keys` owned by the service UID/GID, remounts that auth tree
read-only, and proves H24's historical `/root/.ssh` is absent. It separately
creates the private host-key tree mode 0700 and key mode 0400, both owned only
by the SSH-key-daemon UID/GID. The two identities, homes, groups, files, and
mounts may not alias. PID 1, the forced probe, and the workload never assume
the key-daemon identity. It resets every catchable signal disposition
to default, empties the signal mask, disables any alternate signal stack, sets
the fixed umask/cwd/rlimits, and proves no inherited interval or POSIX timer.
Before release the parent also normalizes and rereads the still-blocked child
to manifest-fixed `SCHED_OTHER`, priority 0, `SCHED_RESET_ON_FORK`, a lower
nice value of +10, one reviewed CPU-affinity/cpuset subset that preserves
native control CPUs, `IOPRIO_CLASS_BE` priority 7, and exact disabled-or-bounded
uclamp state selected by H0 for the current kernel. It proves no RT/RR/DEADLINE
parameters or inherited Android scheduler-group boost remains. The exec
rlimits include `RLIMIT_RTPRIO=0`, `RLIMIT_RTTIME=0`, and `RLIMIT_NICE=0`;
`CAP_SYS_NICE` and `CAP_SYS_RESOURCE` are absent. The positive
filter denies every post-bootstrap scheduler/affinity/nice/ioprio/uclamp or
rlimit-raising operation not explicitly read-only. All descendants inherit the
same lower-priority envelope, while before/after evidence proves native PID 1
and Wi-Fi scheduling state unchanged.
These values and the empty child keyring serial are part of the last pre-exec
receipt. Child namespace teardown drops the only references to that session
keyring; cleanup additionally proves the directly subscribed native
thread/process/session serial/link/count snapshot is unchanged. Static source
validation rejects user-keyring, user-session-keyring, and
`KEYCTL_GET_PERSISTENT` lookups anywhere in the bootstrap. A kernel fixture
proves that missing user, user-session, and persistent keyrings all remain
missing across setup and cleanup.

## Server-side SSH client-authentication boundary

Host-key pinning authenticates the A90 to the attended host; it does not prove
that Dropbear accepts only the intended host client. The separately versioned
minimal-content manifest must therefore bind the exact Dropbear binary hash,
source/configuration provenance, feature matrix, exact argv, account database,
service-home path, forced-command dispatcher, and authentication-file grammar.
The selected server contract is public-key-only client authentication for one
manifest-fixed nonzero service username/UID/GID and exactly one boot-private
client public key. Password, empty-password, `none`, keyboard-interactive/PAM,
root login, every alternate account, and every alternate authorized-key source
are disabled in the bound build and exact launch contract, not merely omitted
from the host's preferred method list.

The account database contains exactly one login-eligible service account. The
distinct SSH-key-daemon account, root, and every other retained system identity
are locked and non-login; duplicate names/IDs, NSS/PAM/network account lookup,
an alternate home, and an alternate shell or key path are forbidden. The
service account has no general shell.
Its read-only auth tmpfs contains exactly one canonical one-line
`authorized_keys` entry: the manifest-selected algorithm and run-bound public
key plus the exact independently validated restrictive key options. Its path,
parent directories, owner/group, mode, size, digest, link count, mount identity,
and absence of symlink/hardlink aliases are reread before release. A duplicate,
comment-only or extra line, unknown option, second key, or parser ambiguity is
`NO_GO`.

Trusted bootstrap, from its proved-clean address space, never reads the host
private bytes. It opens only the exact key, accepted-client-key, fixed-account,
and immutable forced-dispatcher objects, then forks one child that immediately
performs an exact manifest-bound static key-daemon `execveat(AT_EMPTY_PATH)`
before reading the key, binding a listener, or accepting a connection. From its
first instructions the clean daemon closes every unneeded source/path/
directory FD, marks retained descriptors close-on-exec, changes every real/
effective/saved ID to the distinct SSH-key-daemon UID/GID, sets itself
permanently non-dumpable, uses keep-caps only during that trusted identity
transition, sets exactly `CAP_SETUID`/`CAP_SETGID`, clears keep-caps, locks the
reviewed securebits, sets `no_new_privs`, and installs its manifest-bound
inherited filter. It then emits one fixed `KEY_DAEMON_CLEAN_READY` scalar and
only on its sole internal status pipe after its own exact
`/proc/self/maps`/`map_files` check has passed and before loading the key or
binding the listener. Exact source order then permits
it to load the already-open key FD, close it, and bind/listen while every
external ingress rule remains blocked. It emits exact
`KEY_DAEMON_LISTEN_READY`, closes the internal status write end, and reaches
pipe EOF before any accept. Bootstrap validates and forwards the canonical
summary; native PID 1 independently verifies the exact daemon pidfd,
executable, ID/capability/filter/FD set and
current `maps`/`map_files` provenance with no inherited native, shared, device,
deleted, memfd, or unexpected mapping before the daemon can contribute to
`LOCAL_PERSISTENT`; this verification itself never opens ingress or permits an
accepted connection. A missing, reordered, or drifted proof is
`RECOVERY_PARKED`; ingress remains closed. The service UID cannot
traverse the mode-0700 private-key tree or
read its mode-0400 key. The child procfs has no hidepid bypass group, and the
service filter denies `ptrace`, `process_vm_*`, `pidfd_getfd`, process memory/
FD duplication, and any operation that could make the key daemon dumpable or
inspect `/proc/<key-daemon-pid>/{mem,fd,maps,ns}`. Exact negative probes reread
those denials from the service identity.

The key daemon retains only `CAP_SETUID` and `CAP_SETGID`, solely so one
authenticated per-session child can perform the scalar-exact transition to the
fixed service GID/UID. Its all-ABI filter permits only that one
`setresgid(service,service,service)` then
`setresuid(service,service,service)` sequence and the exact Dropbear
listener/session syscall trace; every other credential, group, capability,
file-open, exec, namespace, mount, device, and control operation is denied.
The child enters with empty supplementary groups and no keep-caps state. The
nonzero-to-nonzero ID transition is never assumed to clear capabilities: the
trusted child immediately performs one exact zero-`capset`, clears ambient
capabilities, rereads empty permitted/effective/inheritable/ambient sets and
the fixed service IDs, and cannot regain from the residual bounding bits
because `no_new_privs`, locked securebits, a `nosuid` root, and zero setuid/
file-capability executables are all bound. The parent listener/session engines
remain non-dumpable under the non-login key-daemon identity.

No client-controlled code runs in the authenticated child before the identity
drop. The selected Dropbear source must prove that all host-key FDs are absent
or close-on-exec and every inherited child-side private-key buffer/copy is
explicitly zeroed before one exact `execveat(AT_EMPTY_PATH)` of the prebound
immutable forced dispatcher. Exec replaces the inherited address space; the
dispatcher receives only the exact bounded non-PTY channel descriptors and no
key/config/listener/control FD. The key-daemon parent may retain private
material only for protocol signing/rekey and can emit only protocol output,
never key bytes. Any alternate fork/exec path, missing zeroization, readable
proc surface, retained key FD/buffer, capability or saved-ID regain, second
listener, daemon restart, or unproved Dropbear source behavior is `NO_GO`.

The manifest-pinned Dropbear build and exact argv must disable PTY, password
and interactive authentication, local and remote TCP forwarding, agent
forwarding, X11 forwarding, arbitrary subsystem/command execution, and a
general shell. The sole accepted session is forced to one immutable read-only
PID-1/workload probe dispatcher with an exact request grammar and bounded
output; the server ignores or rejects every client-supplied alternate command
and environment. Build-time feature removal is preferred, and any runtime
option or `authorized_keys` restriction is accepted only after its exact
selected-version source/help/parser semantics are independently bound. If the
two-identity non-root Dropbear build cannot implement this complete matrix,
the candidate is `NO_GO`; a permissive fallback is forbidden.

The attended client uses the exact service username, one private counterpart,
`IdentitiesOnly`/batch public-key-only behavior, no agent, no forwarding, no
PTY, strict host-key checking, and the fixed probe request. Evidence must bind
the negotiated public-key method, accepted public-key fingerprint, account,
forced dispatcher/result, server host-key receipt, target/boot/run nonce, and
native cache digest. A successful connection by any password, empty password,
wrong or second key, root/alternate account, alternate key path, general
command, shell, subsystem, PTY, forwarding, agent, or X11 path is a security
failure rather than a weaker proof.

## Aggregate resource boundary

PID, mount, IPC, UTS, and network namespaces do not reserve global PIDs,
memory, CPU time, or storage I/O. Before any identity allocation, H0/static
analysis of the exact current kernel/config and controller implementation must
select and freeze exactly one reviewed A90 cgroup backend and controller layout
for the future execution-critical manifest. Only after that choice is frozen
may a candidate identity and artifact be allocated. The candidate's later
unarmed F1 boot self-check verifies that exact backend/layout before any D1; it
never selects, autodetects, or falls back. A mixed v1/v2 hierarchy or fallback
to rlimits alone is forbidden. The selected backend must provide aggregate
pids, memory plus swap (or prove swap absent), CPU quota/period, and UFS-device
I/O throttling, plus the exact manifest-frozen cpuset/uclamp or equivalent
backend controls needed by the normalized `SCHED_OTHER` envelope. H0 fixtures
must prove CFS bandwidth and that exact placement preserve the declared native
CPU reserve; RT/RR/DEADLINE inheritance is never an accepted backend case.

The manifest also freezes non-cgroup kernel-object reserves. There is no
devpts/ptmx and therefore no child PTY allocation. The two dedicated nonzero
UIDs separate per-UID pipe and queued-signal accounting from native UID 0;
message queues, SysV IPC, inotify/fanotify, AIO/io_uring, perf, BPF, userfaultfd,
and real-time queued signals are unavailable by the positive syscall policy.
Every descendant inherits exact `RLIMIT_NOFILE`, `RLIMIT_SIGPENDING`,
`RLIMIT_MSGQUEUE=0`, `RLIMIT_MEMLOCK`, `RLIMIT_CORE=0`, stack, and process
limits. `pids.max * RLIMIT_NOFILE`, the maximum socket/pipe/epoll/timer objects,
both dedicated UIDs' pipe pages, and their worst-case kernel memory must remain
below manifest-fixed bounds that leave a measured native recovery reserve in
the exact global file table and related counters. Socket counts are further
bounded by the flow policy below.

H0/static evidence and the later unarmed self-check must prove either exact
kernel-memory cgroup charging for each allowed object class or the conservative
global-reserve calculation; an uncharged or unobservable allowed class is
`NO_GO`. Preflight reads but never writes the exact global limit/use counters.
Cleanup proves the child PID namespace empty, both dedicated UIDs have no
remaining charged object, and every observed native/global counter is within
its permitted monotonic delta. Counter unreadability, overflow, or reserve
violation is `RECOVERY_PARKED`, never a broad global cleanup.

After durable `HANDOFF_INTENT`, native PID 1 creates nonce-bound child cgroup
directories under exact prevalidated controller ancestors without changing an
ancestor. The sole bootstrap child remains blocked while the parent moves its
outer PID into every required controller, writes and rereads exact manifest
limits, and proves the same child is the only member. Descendants inherit those
bounds. The pids limit leaves a fixed system reserve; memory and swap limits
leave a measured native/Wi-Fi reserve; CPU quota preserves a native scheduling
reserve each period; I/O limits bind the freshly resolved UFS whole-device
identity and cap reads and writes. Native PID 1 and every native Wi-Fi task must
remain outside all child groups. No cgroup filesystem or controller FD enters
the child mount or FD tree.

Missing controllers, an unexpected hierarchy/mount/ancestor, limit rounding,
membership drift, unavailable swap or I/O accounting, a limit exceeding its
bound capacity, or inability to keep native reserve is `NO_GO` before child
release. The parent records OOM, throttle, pressure, and pids-limit counters as
evidence only. Cleanup first terminates and reaps the exact PID namespace, then
requires every child group empty, removes only the nonce-bound group in each
controller, and proves native membership and ancestor configuration unchanged.
Crash reconciliation uses the durable intent plus exact controller mount,
ancestor, group inode, limit, and membership receipts; it never broad-writes or
broad-removes cgroup state.

Debian PID 1 and every descendant remain inside that PID namespace. The native
supervisor is absent from Debian `/proc`, and Debian has no `/proc/<native-pid>`
route to a native root, FD, namespace, or device capability.

## Network boundary

The namespaces never share AF_UNIX or netlink control state. The native side
keeps `wlan0` and its exact helper. During the blocked bootstrap, native code
creates one veth pair through a reviewed rtnetlink implementation, moves only
the Debian peer into the child network namespace with the already-bound target
network-namespace FD and exact `IFLA_NET_NS_FD` operation, and binds the
native interface plus moved-peer identity by ifindex, namespace inode, and
boot nonce. The parent opens exactly one `O_RDONLY|O_CLOEXEC` child nsfs FD,
binds its FD number, flags, link target and `st_dev:st_ino`, proves no duplicate,
uses it in that one move message, and closes it immediately after the exact
rtnetlink acknowledgement before native-end configuration or any child
continuation. It then enumerates `/proc/self/fd`/`fdinfo` and proves no parent
descriptor references that nsfs inode. Later namespace checks are path-based or
use one scoped close-on-exec observation FD that is closed and followed by the
same zero-reference enumeration before publishing any result. Native PID 1
never calls `setns` and no helper task is created. No
general `ip`, shell, or host-provided command is used. Moving the peer is not
treated as configuring it: address, route, namespace-local sysctl, link state,
and child-end traffic control remain absent until the separately journaled
child network-preparation phase below.

Before the child peer is configured or released, the native supervisor
installs a dedicated boot-nonce-bound netfilter table through a reviewed
interface. That same transaction preinstalls one exact dormant SSH-ingress
gate: the complete forwarding/NAT rule and its named set/handle exist, but the
one manifest-bound activation element is proved absent, so it cannot match and
all external service ingress remains default-drop. Its table/chain/set/rule
handles, empty-element prestate, zero counters, interface identities, target/
boot/run nonce, and close-only cleanup operation are bound before release; no
later rule construction or replacement is permitted. The first proof is
IPv4-only. Before any veth, rule, or sysctl write,
the supervisor requires a closed compatible precondition over the existing
native network namespace: `net.ipv4.ip_forward=1` plus exact all/default/wlan
forwarding, `rp_filter`, `accept_redirects`, `send_redirects`, and `proxy_arp`
values. It never writes `ip_forward` or an existing all/default/wlan scalar;
any mismatch is `NO_GO` with zero network effect. After creating the
nonce-bound native veth, the parent writes and rereads only that native-end
interface's exact fields and proves the moved peer is no longer configurable
or nameable from the native namespace. After durable `NETWORK_PREP_INTENT`,
the trusted child alone writes and rereads the exact moved-peer address,
prefix, route, link, child-only IPv6-disable and other manifest-frozen child-
namespace fields while holding a bounded `CAP_NET_ADMIN` window. It opens no
payload socket or native-netns handle. One exact bootstrap-only child-local
`NETLINK_ROUTE` socket performs these operations and closes before the receipt;
the child dispatches no userspace payload packet. Any kernel-generated neighbor
or address-control packet must match the predeclared finite grammar and exact
counters. It then removes `CAP_NET_ADMIN` from every
effective, permitted, inheritable, ambient, and bounding set, rereads the
result, publishes the unique `NETWORK_PREPARED` receipt, and blocks again.
Native IPv6 is untouched.
Cleanup deletes the rules and nonce-created veth, then proves all existing
native precondition values are unchanged. Static source checks forbid writes to
`ip_forward` and existing all/default/wlan paths. An unsupported or malformed
precondition, write outside the new interface/child namespace, reread failure,
or ambiguity is `RECOVERY_PARKED`; no global default is guessed or restored.

Cgroup accounting alone does not bound the native-network-namespace softirq,
skb/qdisc backlog, conntrack memory, or Wi-Fi airtime caused by Debian traffic.
Before any identity allocation, H0/static evidence must therefore select and
freeze one exact kernel-supported traffic-control and conntrack mechanism.
Runtime never autodetects or falls back. Before network preparation the native
supervisor sets and rereads the native-end MTU, `txqueuelen`, and exact ingress
and egress packet/byte rate, burst, and queue-depth bounds. During the one
bounded network-preparation continuation, the trusted child sets and rereads
the corresponding manifest-fixed peer-end values and handles, then permanently
drops `CAP_NET_ADMIN`. The combined native receipt and unique child receipt
bind every qdisc, filter, and action by namespace, ifindex, handle, kind, and
options. After `NETWORK_PREPARED` the child has no capability or control
endpoint with which to change them.

The nonce-bound netfilter policy assigns all permitted veth traffic to one
dedicated conntrack zone and enforces both a maximum new-flow rate and a
maximum concurrent-flow set before forwarding or NAT. Flow-table and hardware
offload are forbidden for the first proof. No global conntrack sysctl, existing
Wi-Fi qdisc, or other interface is changed. Missing per-zone accounting or
delete support, an unsupported qdisc/action, counter wrap or unreadability,
limit/handle drift, or inability to preserve a measured native Wi-Fi/control
reserve is `NO_GO` before release.

Cleanup first blocks new traffic, then drains or deletes only the bound zone's
entries, deletes the exact qdiscs/filters/actions and veth pair, and proves all
zone state, queues, handles, and nonce-created interfaces absent while existing
Wi-Fi qdiscs, global conntrack settings, and native network state remain
configuration- and identity-equivalent to their pre-intent receipt. Existing
packet/byte counters may only advance monotonically through the separately
accounted permitted Wi-Fi path; they are never reset or compared as immutable
bytes. Crash reconciliation uses
only the durable nonce, zone, handle, counter, and interface identities; it
never flushes a global table, qdisc, or conntrack state.

The closed policy covers native local delivery as well as routed
traffic:

- default drop in both forwarding directions;
- native-veth `INPUT` defaults to drop, including packets addressed to the
  native veth peer, native-owned addresses, or a wildcard-bound native socket;
- native `OUTPUT` toward the Debian peer defaults to drop except exact
  kernel-required neighbor/control responses; no native application opens a
  local service or initiates a connection across this boundary;
- established/related return traffic only;
- outbound TCP/UDP from the Debian veth subject to exact egress policy;
- one preinstalled but dormant selected inbound server path to a non-privileged
  Debian listener; it cannot match until the separately journaled one-element
  activation after `LOCAL_PERSISTENT`;
- no local delivery or forwarding to native management, Binder/property
  sockets, USB, loopback, link-local control, or other device interfaces;
- exact table/chain/rule handles, per-rule counters, interface identities,
  boot nonce, and removal receipt.

The permitted neighbor/control exception is a closed packet-type/address
allowlist required only to establish the veth link; it carries no TCP or UDP
payload and cannot address a native listener. Any native-veth `INPUT` accept,
unexpected native-to-Debian `OUTPUT`, wildcard-listener reachability, extra
rule, handle drift, or nonzero denied-path counter fails before child release.
Cleanup removes only the exact bound table and proves every recorded handle
absent; uncertainty is `RECOVERY_PARKED`.

The only ingress-opening effect is one reviewed atomic netfilter transaction
that inserts the exact prebound activation element into that already-existing
set. It may run only after durable `INGRESS_OPEN_INTENT` and never constructs,
replaces, or retries a rule. Exact command return plus an independent table/
set/rule/counter readback publishes `INGRESS_OPEN`; a missing or torn return,
wrong handle/element, duplicate element, counter drift, or readback failure is
never resent. Reconciliation first uses only the predeclared close-only
operation to remove that exact element when table identity is complete, proves
the gate dormant, and enters `RECOVERY_PARKED`; if identity is incomplete it
parks for attended recovery without guessing or flushing global state.

Concrete addresses and device-private network values are generated or loaded
from boot-private state and remain under `workspace/private/`; none enters the
tracked manifest, report, or log. DNS input is materialized in a bounded
Debian tmpfs file from boot-private configuration, never an SD property root.

Before Debian exec, the bootstrap drops `CAP_NET_ADMIN`, `CAP_NET_RAW`,
`CAP_SYS_ADMIN`, `CAP_SYS_PTRACE`, `CAP_MKNOD`, `CAP_DAC_OVERRIDE`,
`CAP_DAC_READ_SEARCH`, `CAP_FOWNER`, and every capability not in the
reviewed server minimum from the permitted/effective/inheritable/ambient and
bounding sets. That minimum is empty for PID 1, probe, workload, and every
service-UID process; only the filtered non-login key-daemon parents retain the
exact `CAP_SETUID`/`CAP_SETGID` pair described above. The selected server binds
a non-privileged internal port, so it does not need `CAP_NET_BIND_SERVICE`. No Debian process can move `wlan0`, alter
routes/rules, open raw packet sockets, or enter a native namespace.

The new rootfs manifest contains no setuid or file-capability executable and
the UFS mount remains `nosuid`. Before exec the bootstrap also clears ambient
capabilities, sets and verifies `PR_SET_NO_NEW_PRIVS`, and locks the reviewed
securebits against root/setuid capability regain. Any capability retained for
the selected consoleless PID 1 or Dropbear is an explicit finite manifest field
justified by a static
service trace; it cannot include namespace, mount, device, ptrace, raw-network,
or network-administration authority. Failure to derive that exact service
minimum is `NO_GO`.

Kernel support for PID/mount/IPC/UTS/network namespaces, the frozen cgroup
backend, veth, the exact netfilter operations, per-namespace procfs, and
capability bounding is a host/build plus unarmed boot self-check gate. Missing
support is `NO_GO`; neither a shared network namespace nor a userspace proxy is
an allowed fallback.

## Handoff state machine

All records are private regular mode-0600 files published temp-fsync,
atomic-no-replace, and directory-fsync. Existing, linked, wrong-mode, torn, or
extra members fail closed.

1. `BOOT_HEALTHY`: exact resident self-test, rollback, recovery, Wi-Fi, UFS,
   content, boot-private inputs, and the unchanged ordinary native cloning-
   thread scheduler precondition validate while unarmed.
2. `HANDOFF_INTENT`: bind boot generation, candidate identity, UFS identity,
   native Wi-Fi health, namespace/network/resource plan, and maximum one child
   launch.
3. `CHILD_BLOCKED`: clone exactly one bootstrap child, require the unique
   inherited-mm close/one-exec branch to enter the manifest-bound static clean
   bootstrap, require the unique no-effect `CHILD_READY` frame followed by an
   empty-control-pipe read, send one pidfd `SIGSTOP` from the parent, and bind
   PID/start time, pidfd, clean executable and exact `maps`/`map_files`
   provenance, namespace inodes, pipe identities/emptiness, an exact parent-side
   `/proc/<pid>/fd` enumeration containing only the control-read and receipt-
   write ends with `FD_CLOEXEC` re-armed, and
   `waitid(P_PIDFD, ..., WSTOPPED)` initial stopped state. Any other frame or
   effect before this stop is `RECOVERY_PARKED`.
4. `RESOURCE_READY`: move the still-blocked child into every exact cgroup,
   apply and reread the complete scheduler/affinity/ioprio/uclamp envelope,
   verify aggregate pids/memory+swap/CPU/I/O limits and native reserves, and
   prove no native member or ancestor drift. No child continuation has occurred.
5. `NETWORK_PARENT_READY`: prove existing native sysctls already compatible
   without writing them, create/bind the veth, use the exact child-netns FD to
   move only the peer without `setns`, bind the FD number/flags/nsfs inode and
   exact move acknowledgement, immediately close it, and prove no duplicated or
   other parent nsfs FD references that child namespace before configuring only
   the native end. Then install
   its exact bidirectional rate/burst/queue bounds plus a dedicated conntrack
   zone with new-flow/concurrent-flow limits, and install exact native `INPUT`,
   `OUTPUT`, forwarding, and NAT rules. The moved peer still has no address,
   route, child-local sysctl change, or up state. Require zero packets and prove
   no native local listener is reachable from the child peer. This state and
   every later parent observation require zero retained child-namespace FDs.
6. `NETWORK_PREP_INTENT`: durably bind the exact pidfd, one-byte `N`
   (`NETWORK_PREPARE`) opcode, first continuation count, parent/network digests,
   and the sole permitted child-network setup before sending anything. The
   parent atomically writes `N` to the otherwise-empty control pipe and sends
   one pidfd `SIGCONT`. Either missing dispatch result is uncertain and never
   retried; a PID-number signal is forbidden.
7. `NETWORK_PREPARED`: the trusted child may use `CAP_NET_ADMIN` only inside
   its already-created network namespace to set and reread the exact moved-
   peer name/ifindex, MTU, queue, address/prefix, default route, child-only
   sysctls, link state, and peer-end traffic-control handles through one exact
   child-local bootstrap-only `NETLINK_ROUTE` socket, then closes that socket.
   It opens no payload socket and dispatches no userspace payload; any kernel
   neighbor/address-control packet must match the finite reviewed grammar and
   counters. It permanently drops `CAP_NET_ADMIN`
   from effective, permitted, inheritable, ambient, and bounding sets, emits
   one bounded readback receipt, and blocks on the empty control pipe. The
   parent sends a second pidfd `SIGSTOP`, proves the stopped event, receipt,
   outer identity, native-side handles/counters, and `/proc/<pid>/status`
   capability absence, independently re-enumerates the same exact two-pipe FD
   set with no retained netlink socket, and revalidates the unchanged clean
   bootstrap mapping provenance. Any partial setup, userspace payload or unaccounted
   kernel packet, extra route/interface,
   capability retention, wrong frame, or missing stop is `RECOVERY_PARKED`.
8. `ROOT_PREP_INTENT`: durably bind the exact pidfd, one-byte `R`
   (`ROOT_PREPARE`) opcode, second continuation count, exact
   `NETWORK_PREPARED` digest, and sole permitted private root/key-preparation
   stage. Only after that record does the parent atomically write `R` and send
   one pidfd `SIGCONT`; a missing result is uncertain and never retried.
9. `ROOT_PREPARED`: the trusted child may now do only this bounded phase with
   `CAP_NET_ADMIN` already absent:
   first reprove the two-end bootstrap FD set, then privately mount and validate UFS,
   writable tmpfs, procfs/sysfs/minimal-dev, Debian init, and the old-root
   removal plan. From the proved-clean bootstrap mm it forks exactly one helper
   that immediately performs an exact manifest-bound static generator exec
   before reading entropy or key material. The generator's own early barrier
   emits `GENERATOR_CLEAN_READY` on its sole internal status pipe and proves
   exact `/proc/<pid>/exe`, `maps`, `map_files`, and no inherited native mapping
   before generation. It is the sole pre-`ROOT_PREPARED` private-key
   memory exception. Before key generation the generator is permanently
   non-dumpable, has `RLIMIT_CORE=0`,
   has the exact executable/argv/environment/UID/GID/capability/stdio/FD set,
   and has no core, log, socket, or foreign output sink. Frozen source and
   negative fixtures prove that it can create only the one absent `O_EXCL`
   key file and one bounded public-only `GENERATOR_PUBLIC_COMPLETE` receipt on
   that same internal channel, then must close the writer and produce EOF before
   exact exit/reap; never private-key output. Bootstrap validates the two
   generator frames, FD set, and EOF and alone forwards their canonical scalar
   summary on the native receipt. It
   generates exactly one per-boot Ed25519 host key in the private
   `/etc/dropbear` tmpfs, proves a mode-0700 private tree, mode-0400 key, exact
   SSH-key-daemon UID/GID ownership, one link, and absence before creation,
   then exits and is ownership-aware reaped. The child proves the generator
   PID/FD/address-space is gone and that no core, log, temporary file, second
   key, or private-output artifact exists; generator crash, signal, private
   output, ambiguous reap, or residue is `RECOVERY_PARKED`. Only after that
   proof does it bind the exact private-file inode/size/hash without exporting
   its bytes, remount that exact tmpfs read-only, and reread the file/mount
   identity. It sends only the exact
   algorithm, public key, and SHA-256 fingerprint in its bounded bootstrap
   receipt, then blocks reading the again-empty control pipe without pivot,
   capability/UID drop, or exec. The parent requires the complete unique frame,
   sends a third pidfd `SIGSTOP`, proves a new pidfd-bound stopped event and empty
   pipe, and binds unchanged outer identity, normalized scheduler state, and
   every prepared mount/file digest plus the independently enumerated exact
   two-pipe FD set and clean bootstrap mapping provenance before publishing
   `ROOT_PREPARED`.
10. `CHILD_RELEASE_INTENT`: durably record the exact third/final continuation
   count, one-byte `X` (`RELEASE`) opcode, empty control-pipe proof, and prepared
   network/root digests. The parent atomically writes `X`, then sends the final
   pidfd-bound `SIGCONT`.
11. `CHILD_RELEASED`: after all three token/signal dispatches return exact
   success, bind their pipe/pidfd results without permitting retry. Only the
   exact `X` opcode and return from the third stop permit pivot, old-root
   detach, the one clean-exec filtered non-dumpable SSH-key-daemon launch,
   final service capability/UID/filter envelope, and PID-1 exec. All external
   service ingress remains blocked. A crash after intent with any required token-write or
   pidfd-signal dispatch result missing is uncertain and never resends. Early exec,
   wrong token/stop/pidfd, an extra token or
   continuation, or an unacknowledged stage is `RECOVERY_PARKED`.
12. `KEY_DAEMON_LOCAL_READY`: the clean daemon self-verifies and emits
    `KEY_DAEMON_CLEAN_READY` on its internal status pipe before key load/
    listener bind, then may load/close the key FD and bind/listen only behind
    blocked ingress. It emits `KEY_DAEMON_LISTEN_READY` and closes that channel
    before accept; bootstrap validates exact EOF and alone forwards the summary
    on the native receipt. Native PID 1 independently binds the daemon pidfd, executable, non-login IDs,
    non-dumpable/two-cap filter, exact FDs and clean `maps`/`map_files`. The
    daemon closes both bootstrap-pipe ends and every root/key source FD before
    any accept. Missing or reordered proof leaves ingress closed and enters
    `RECOVERY_PARKED`.
13. `DEBIAN_EXEC_LOCAL`: the bootstrap publishes its final pre-exec frame and
   exec closes the only child write end. The parent combines pipe EOF with the
   same pidfd, exact outer PID/start time, non-exit status, and exact
   `/proc/<outer-pid>/exe` identity plus the manifest-bound key-daemon
   identity/listener/non-dumpable/capability/FD facts to record a local exec
   observation. EOF alone is never success and no post-exec writer is assumed.
14. `LOCAL_PERSISTENT`: the parent observes only local facts: the same Debian
    pidfd remains live, exact namespaces/mounts/network rules remain bound, the
    one key-daemon/listener tree retains its non-login IDs, non-dumpable state,
    two-cap filter, exact clean-exec mapping provenance and bounded session
    count, no service task has a key FD or daemon-proc access, and no denied-
    path counter advances. It also rereads the exact dormant ingress handle,
    absent activation element, zero pre-open counters, and default-drop policy.
    It cannot open ingress or claim SSH authentication.
15. `INGRESS_OPEN_INTENT`: durably bind `LOCAL_PERSISTENT`, the exact target/
    boot/run and table/chain/set/rule/element identities, empty-element
    prestate, counters, one atomic activation operation, and the close-only
    cleanup operation before dispatch. Only this record permits one activation;
    it never permits rule construction, replacement, or a second dispatch.
16. `INGRESS_OPEN`: after that sole transaction returns exact success, the
    parent independently rereads the same table/set/rule and proves exactly one
    expected activation element, the single manifest-bound SSH path open, all
    other ingress still default-drop, and exact pre-host counters. It durably
    binds the dispatch result and readback before a host may connect. A missing
    or torn result, wrong/duplicate element or handle, counter drift, or readback
    failure is never resent: exact-identity cleanup removes only the activation
    element and proves the gate dormant before `RECOVERY_PARKED`; incomplete
    identity parks with no guessed global cleanup.
17. `HOST_AUTHENTICATED`: the exact current `INGRESS_OPEN` record is mandatory.
    Before any SSH attempt, a separate attended host observer retrieves the
    exact target-, resident-, boot-, run-, child-pidfd-,
    and cache-digest-bound host-key receipt through the dedicated read-only
    native frame. It publishes a no-clobber private `known_hosts` entry from the
    retrieved algorithm and public key, verifies the retrieved SHA-256
    fingerprint, and only then may the separate attended host observer reach
    the exact forwarded port with `StrictHostKeyChecking=yes`. TOFU and
    `StrictHostKeyChecking=no` are forbidden. Only after the server key matches
    may it authenticate as the one manifest-fixed service account with the one
    boot-private client key. The transcript must prove that the negotiated
    client method was public key, the accepted key fingerprint was exact, and
    the server forced the immutable read-only PID-1/workload probe. The client
    uses no agent, password, interactive method, PTY, forwarding, subsystem, or
    alternate command. Its durable journal binds the exact account, method,
    key fingerprint, forced-probe result, device boot/run nonce, and native
    cache evidence digest. Only that combined host result may publish
    `HEALTH_PENDING_PERSISTENT_DEBIAN`; the native parent never fabricates a
    service-ready record.
18. `PERSISTENT`: parent remains in a bounded supervisor loop and never claims
    final resident health. Missing or failed host authentication causes an
    attended return/recovery; automatic cleanup is reserved for exact local
    child/invariant failure.
19. `RETURN`: attended reboot or failure cleanup first removes and proves absent
    the exact ingress activation element and proves the parent has no child-
    namespace nsfs descriptor or duplicate, then terminates the exact Debian
    PID namespace, removes only bound network rules/interfaces, proves the
    child mount namespace gone, and verifies exact native health before
    `RESIDENT_HEALTHY`.

No stage resends candidate transfer, launches another Debian child, opens
ingress twice, or applies a network rule twice. `NETWORK_PREP_INTENT`, `ROOT_PREP_INTENT`, and
`CHILD_RELEASE_INTENT` each precede one fixed one-byte control opcode and one
pidfd continuation; `INGRESS_OPEN_INTENT` separately precedes the sole dormant-
gate activation. Recovery never resends any token, signal, or ingress-open
transaction. EOF, wrong
token, or a token without its exact signal result fails closed. A crash or
error after the first continuation
kills/reaps the exact child and removes only
bound private/resource/network state when identity is complete, otherwise it
parks for attended recovery. Crash reconciliation reads the durable stage and
current pidfd/namespace/rule identities. Ambiguity parks for attended recovery.
An `INGRESS_OPEN_INTENT` prefix is observation-and-close-only: reconciliation
never inserts the activation element, and a missing activation result can never
be promoted to `INGRESS_OPEN` from a permissive inference. It closes the exact
element when identity is complete and otherwise remains `RECOVERY_PARKED`.

## Logging and evidence

The SD card is not a runtime dependency. Native PID 1 writes compact bounded
records under an exact cache-backed evidence directory. Debian receives no
write handle to that directory. Two `pipe2(O_CLOEXEC)` channels exist only
during trusted bootstrap: one parent-to-child control pipe accepts exactly the
one-byte `N` (`NETWORK_PREPARE`), `R` (`ROOT_PREPARE`), then `X` (`RELEASE`)
sequence, and one child-to-parent
receipt pipe carries fixed-schema stages and failures. Both reject extras,
wrong order, EOF, partial writes, and byte/rate overflow. Unused ends close
immediately; the child control end closes before exec and successful exec
closes the sole receipt write end. Neither is duplicated to a fixed post-exec
descriptor. Pipes never carry FDs; ancillary data and AF_UNIX transport are
absent.

Those are the only native-facing pipes and the clean bootstrap is their sole
receipt writer. No helper may write them or carry them across its clean exec.
For generator and key-daemon clean execs bootstrap creates, one at a time, one exact internal
`pipe2(O_CLOEXEC)` status channel: bootstrap retains the read end; the forked
helper's only permitted pre-exec actions are to close both main-pipe ends and
every unrelated FD, clear
`FD_CLOEXEC` only on the internal status write end plus the exact manifest-
listed input FDs needed by that one exec, and exact-execs. The first helper
instructions re-arm close-on-exec on every retained FD, reread fd/fdinfo, and
emit fixed frames as the sole writer. The generator channel permits exactly
`GENERATOR_CLEAN_READY` then one bounded public-only
`GENERATOR_PUBLIC_COMPLETE`, closes before exact exit/reap, and reaches EOF.
The daemon channel permits exactly `KEY_DAEMON_CLEAN_READY` then
`KEY_DAEMON_LISTEN_READY`, closes before any accept, and reaches EOF while the
daemon remains live. Bootstrap binds the helper pid/start/pidfd, frame order,
byte cap, FD set and terminal EOF, closes the internal read end, and alone
forwards a canonical scalar summary over the native receipt. At every main
stop barrier only the original two bootstrap ends remain. Wrong writer,
multiple writers, an inherited main-pipe end, extra FD, frame interleave,
partial/duplicate/extra frame, premature/late EOF, helper crash, or internal
pipe residue is `RECOVERY_PARKED`; no frame is inferred or replayed.

After exec, native evidence consists solely of parent-observed pidfd, process,
namespace, mount, rule/counter, exit, and cleanup facts. Native PID 1 does not
claim Debian application logs or authenticated service health. A dedicated
read-only resident retrieval frame, separate from the general shell and its
orphan reaper, exports the bounded native cache digest to the attended host.
The host stores the exact SSH handshake, validated per-boot host-key receipt,
fixed read-only PID-1/workload probe, and matching boot/run nonce under private
evidence and combines them without sending a service-ready assertion back to
native. A first-seen network key is never an authentication root.

The per-boot Ed25519 host-key file exists only in the isolated child's private
mode-0700 `/etc/dropbear` tmpfs, mode 0400 and owned by the non-login
SSH-key-daemon identity. Trusted bootstrap uses the exact manifest-pinned
generator under the transient non-dumpable/zero-core/no-private-output
exception above, requires usable entropy, creates the key once, fully reaps
that bounded helper, and proves its PID/FD/address-space plus every core/log/
temporary/private-output artifact absent. During that bounded generation only,
private bytes may exist in the one key file and the sole generator address
space. After the successful reap and before daemon launch, they may exist only
in the file; after the daemon loads it, they may exist only in that file and
the non-dumpable filtered key-daemon signing memory. Trusted bootstrap binds
the private-file inode/size/hash locally, binds the public material to the
native cache receipt, and remounts the exact host-key tmpfs read-only before
child release. It rereads the mount identity/options and private-file metadata/
hash. No other process may load the private bytes; the service identity cannot
traverse the tree, inspect that process, inherit a key FD or buffer, or regain
the daemon identity. No descendant can replace, unlink, rewrite, or rotate the
key.
The dedicated retrieval returns only algorithm, public key, fingerprint, and
the target/resident/boot/run/pidfd/cache binding; neither retrieval nor any
service/probe/workload path exports private key bytes. Missing or duplicate
keys, wrong metadata, parse or fingerprint errors,
receipt duplication, stale-run reuse, within-run key rotation, or a presented
key mismatch is `NO_PROOF` and requires attended return/recovery. Cleanup of
the exact child first blocks new sessions, terminates and reaps the bound
listener/session engines, proves every key-daemon PID/FD and both dedicated-UID
resource sets gone, then destroys the key tmpfs with the mount namespace. A later boot must
generate and retrieve a different receipt; an earlier `known_hosts` entry is
not reusable.

The exact public audit in
`A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md`
rejects the immutable H14/H24 demonstration content for this first proof. Its
12,092-byte firstboot can start Dropbear, but also configures legacy `ncm0`,
smoke, HUD-intent, and Debian Wi-Fi paths and has no post-exec receipt writer.
A separately versioned minimal rootfs/content manifest is therefore a
pre-candidate requirement, not a later optimization. It supplies the exact
manifest-pinned, public-key-only Dropbear/key-daemon build and immutable forced
dispatcher; trusted bootstrap launches the listener under the distinct
non-login key identity before the service UID's PID-1 exec. The rootfs then
starts only the selected workload on the bootstrap-configured veth. It binds
one login-eligible fixed service account,
one canonical boot-private client key, one forced read-only probe, and no
password/interactive/root/alternate-account/shell/subsystem/PTY/forwarding/
agent/X11 path. It consumes authorization from the manifest-fixed service home
rather than `/root/.ssh`, and never creates, replaces, rotates, or reads the
server private key from the service identity. PID 1 and the forced dispatcher
inherit no private descriptor or key buffer and use only the declared writable
set.
Building or reviewing it grants no UFS installation
authority. The current common contract does not activate direct UFS
filesystem-content mutation; a future installation therefore requires a
separately reviewed higher-precedence boundary change, an exact target-contract
process, and attended approval. Until all three exist the successor is
`NO_GO`. Post-exec application-log
export is deferred unless it is explicitly included in that new content
contract; it is not required or overclaimed by the first proof.

Native-required stage stamps use `CLOCK_BOOTTIME`: resident ready, Wi-Fi ready,
intent, clone, network ready, UFS mount/validation, pivot, locally observed
Debian exec, and failure/fallback. The attended host records SSH-ready latency
on its own monotonic clock and binds the device boot/run nonce; it is not
misrepresented as a native `CLOCK_BOOTTIME` sample. Missing telemetry is `na`,
never a safety failure unless the timestamp is itself the required transition
receipt.

## Failure and fallback

Because native PID 1 never leaves its root/namespace, failure does not require a
reverse `switch_root`:

- before `CHILD_RELEASED`, first block every new veth traffic path and SSH
  accept/session path, then durably publish the immutable original failure
  stage/return/errno plus cleanup intent and the exact bound PID/namespace/
  zone/queue/rule/ingress-element/interface/cgroup identities. Only after that durable record
  kill/reap the blocked child, remove only those exact objects and now-empty
  child cgroups, after proving no parent child-namespace FD can pin them, and
  prove its private namespaces disappear. Append the cleanup
  result separately without replacing the original failure, then resume the
  native recovery surface;
- after release but before persistent health, first block every new veth
  traffic path and SSH accept/session path by removing and proving absent the
  exact activation element when present, then durably publish the immutable
  original failure stage/return/errno plus cleanup intent and the exact bound
  PID/namespace/zone/queue/rule/ingress-element/interface/cgroup identities and
  the zero parent-nsfs-FD proof. Only after that
  durable record terminate the exact child PID namespace and prove every
  member gone; only after that proof remove those exact network objects, prove
  native sysctl/qdisc/conntrack configuration unchanged, and remove empty
  child cgroups. Append the cleanup result separately without replacing the
  original failure, then restore the native recovery surface;
- after persistent service begins, remain `HEALTH_PENDING_PERSISTENT_DEBIAN`;
  an unexpected Debian exit performs cleanup but requires attended health
  closure, not automatic relaunch;
- an uncertain child/rule/mount identity or cleanup failure enters
  `RECOVERY_PARKED`; it never broad-kills, broad-unmounts, or guesses;
- a boot-candidate failure uses only the already reviewed boot rollback path.

Fallback means return to the same native resident in memory or an attended
reboot to the exact rollback. It never writes a non-boot partition, formats
UFS, replays handoff, or silently degrades to shared namespaces.

## Production minimum and removals

Keep in the formal successor:

- native supervisor, exact native Wi-Fi owner, isolated Debian bootstrap;
- boot-only rollback/recovery and one-shot journal;
- UFS manifest/read-only root/minimal writable set;
- veth/netfilter boundary with dormant ingress, durable one-shot activation/
  readback/close-only cleanup, host-observed SSH/workload health, compact native
  evidence;
- power/reboot/recovery control required for an attended return.

Exclude from the formal successor:

- persistent native HUD, display success, DRM presenter, boot chime;
- firstboot overlay and smoke HTTP demo;
- retired W0/atomic ownership transaction and all seccomp-notification brokers;
- general shell `cat`/`run` as a health or inventory mechanism;
- SD evidence bind and SD property root;
- benchmark logic from safety predicates.

Retain generic display-owner release only until the first headless candidate
proves no DRM owner at handoff. It is then eligible for a separate reduction,
not silently removed in the same experiment.

## Performance and test functions

Safety gates measure identities and state, not benchmark scores. Test-only
telemetry records:

- boot-to-Debian-exec and boot-to-authenticated-SSH latency;
- UFS mount/content-check time and read throughput;
- veth forwarding throughput, latency, drops, and CPU cost;
- native supervisor and Wi-Fi helper CPU/RSS/wakeup counts;
- Debian workload CPU/RSS, temperature, and normalized clocks when available;
- failure cleanup and attended return time.

The current benchmark only recognizes the SD whole-device name and must be
extended to the exact UFS whole device before UFS comparison. Temperature,
clock, and power are observational; absence is `na`. The initial production
baseline is compared before Full-LTO or other compiler optimization. LTO is a
separate build experiment after functional and recovery closure.

## Required verification before identity allocation

H0/static:

- prove kernel/toolchain support for all namespaces, exact cgroup backend and
  pids/memory+swap/CPU/I/O controllers, veth, exact rtnetlink/netfilter/sysctl
  operations, pidfd/wait semantics, pivot_root, and capability drops;
- compile/link the minimal profile and prove HUD/W0/SD code unreachable;
- negative tests for inherited procfs/old-root/dev/FD, native task visibility,
  an inherited native anonymous secret VMA, `MAP_SHARED` file/device mapping,
  deleted or memfd mapping, wrong bootstrap executable, writable-executable
  VMA, `maps`/`map_files` drift at any stop, a generator that reads key bytes
  before its clean exec, or a key daemon that loads/binds before
  `KEY_DAEMON_CLEAN_READY`,
  a writable `/proc/sys` or `sysrq-trigger`, writable `oom_score_adj`, a visible
  masked kernel/KASLR/device view, unknown proc top-level entry, mask/mount
  drift, later module load/unload, or service dependence on a denied proc write,
  `/dev/console` or `ttyGS0`, wrong rdev, an extra character/block node, any
  devpts/ptmx/tty/PTY, controlling-tty acquisition, wrong stdio description,
  writable root `/dev` or urandom node, `/dev/random`, unexpected submount,
  PTY request acceptance, console/getty service activation,
  any native sysfs mount/bind, surviving UFS block node/FD, shared SysV IPC,
  POSIX mqueue or `/dev/shm` object, shared AF_UNIX/netlink, wrong namespace/
  ifindex, extra forwarding rule,
  native-veth INPUT/local-listener reachability, unexpected native OUTPUT,
  capability retention, `CLONE_NEWUSER` and every other post-bootstrap
  namespace flag, `unshare`/`setns`, `clone3`, unknown legacy-clone flags,
  proc/sysfs remount, every new mount API, device-node recreation, UFS device
  inode open under `nodev`, unexpected inherited socket FDs, AF_QIPCRTR/QRTR,
  netlink and
  kobject uevent, packet/raw, Bluetooth, NFC, VSOCK, CAN, XDP, unknown socket
  families/types/protocols, compat `socketcall`, child replay, torn journal,
  bootstrap-pipe inheritance, a helper carrying or writing a native-facing
  pipe across its clean exec, wrong or multiple internal-status writer, extra
  helper FD, frame interleave, partial/duplicate/extra helper frame, premature
  or late helper EOF, daemon accept before status EOF, helper crash or channel
  residue,
  generic-reaper interception, pidfd/PID mismatch, capability regain,
  EOF-without-exec, SSH before host-key receipt retrieval, TOFU, forged/MITM
  server keys, missing or duplicate server keys, within-run key rotation,
  stale `known_hosts` reuse, forged host SSH/run-nonce binding, private-key
  persistence after child cleanup, service-UID traversal/read of the key tree,
  aliased key/service UID or GID, key-daemon dumpability or `/proc` mem/fd/maps/
  ns access, ptrace/process-vm/pidfd-getfd duplication, retained key FD/buffer
  in the forced dispatcher, missing pre-exec zeroization, wrong saved IDs or
  capabilities, arbitrary identity transition, second/restarted listener,
  password/empty-password/`none`/keyboard-
  interactive or PAM acceptance, wrong or second client key, duplicate or
  extra `authorized_keys` line, alternate auth file/home, root or alternate
  account login, account-database or Dropbear build/config/argv drift, general
  shell or arbitrary command/subsystem execution, and PTY/local-forward/
  remote-forward/agent/X11 acceptance, plus cleanup ambiguity;
- barrier negatives for any child effect or any frame other than the unique
  `CHILD_READY` receipt before the first parent pidfd stop, a missing empty-
  control-pipe block, wrong/extra/partial token, control-pipe EOF, missing or
  wrong pidfd stop sequence, native `setns`, wrong/stale child-netns FD or peer
  move, child-network continuation before durable intent, partial address/
  route/sysctl/qdisc setup, any userspace payload or unaccounted pre-release
  packet, wrong or missing
  `NETWORK_PREPARED` frame/second stop, retained or regained `CAP_NET_ADMIN`,
  a retained `NETLINK_ROUTE` socket or any unexpected child FD,
  root continuation before durable intent, stop without the unique
  `ROOT_PREPARED` frame, root frame without the third stop, early pivot/exec,
  PID-number signaling, torn final-dispatch result, extra continuation, and any
  attempted token or signal replay;
- negative ingress-gate tests for host access before `INGRESS_OPEN`, activation
  before durable `INGRESS_OPEN_INTENT`, crash before/during/after activation,
  missing/torn dispatch return, wrong or duplicate table/set/rule/element,
  counter/readback drift, duplicate open, any resend, wrong-handle cleanup,
  failure to prove the gate dormant, and child termination before ingress close;
- negative parent-namespace-handle tests for stale/wrong FD identity, duplicate
  nsfs FD, `FD_CLOEXEC` drift, move-ack failure, close failure, a retained or
  late-opened child netns/mount/IPC/UTS/PID handle, publication before zero-FD
  enumeration, and cleanup with a namespace still pinned by a parent FD;
- negative tests for inherited thread/process/session keyrings, native user or
  persistent-key reachability, nonempty anonymous session state, visible
  `/proc/keys`, missing syscall-ABI coverage, permitted `keyctl`/`add_key`/
  `request_key`, any user/user-session/`KEYCTL_GET_PERSISTENT` lookup, creation
  of an initially missing user, user-session, or persistent keyring, exec
  environment/group/signal drift, and native-keyring change;
- positive fork/service-start compatibility tests under the exact inherited
  filter plus negatives for filter removal, missing ABI coverage, and a child
  attempting a nested user/mount/PID/network namespace or native-rdev path;
- negative fork, memory, swap, CPU, and UFS-I/O exhaustion tests that hit each
  child bound while native PID 1, Wi-Fi, recovery, and evidence remain
  schedulable; cgroup membership/ancestor drift and partial cleanup tests;
- negative inherited `SCHED_FIFO`, `SCHED_RR`, `SCHED_DEADLINE`, high-priority
  nice, reset-on-fork, affinity/cpuset, ioprio, Android scheduler-group and
  uclamp drift tests; post-exec attempts to change any of them or raise rlimits
  must fail while native scheduling identities remain unchanged;
- negative global file-table, FD, pipe-page, socket, epoll, timer, per-UID
  queued-signal and kernel-memory exhaustion tests; prove ptmx/devpts and PTY
  allocation absent, `GRND_RANDOM` denied, unknown syscalls fail, and every
  dedicated-UID/global reserve plus empty-cleanup counter remains exact;
- negative creation probes for perf/BPF/userfaultfd/io_uring/AIO,
  inotify/fanotify, POSIX mqueue, SysV IPC, module/kexec/syslog control, and
  untraced ioctl/fcntl/prctl operations under the default-deny policy;
- negative UDP/small-packet flood, SYN/new-flow churn, concurrent-flow overflow,
  return-path flood, queue saturation, counter wrap/read failure, qdisc or zone
  drift, partial network teardown, and unsupported-offload tests while native
  control, Wi-Fi, recovery, and evidence remain schedulable;
- UTS mutation tests plus native forwarding-sysctl wrong-value/no-write,
  forbidden `ip_forward`/all/default/wlan write, new-veth partial-write,
  crash-prefix, and existing-field drift tests;
- crash-prefix tests for every state-machine boundary;
- source/size decomposition review if native additions exceed 900 nonblank
  lines or the host runner exceeds 700 nonblank lines.

Fresh candidate unarmed boot self-check, later under a separately qualified F1:

- verify the already manifest-frozen cgroup backend/controller layout without
  selection or fallback; create and destroy its exact child groups plus the
  namespaces/veth/rules without UFS or Debian exec, prove full restoration,
  and store a boot-origin immutable receipt;
- never rerun or overwrite that boot receipt through a manual command.

Only after the H0/static backend selection and other host gates pass may a
fresh successor identity, manifest, and candidate artifact be proposed. The
candidate's separately qualified unarmed F1 self-check must then verify the
frozen backend and full transient restoration before any D1 approval. This H0
design itself grants none.

## Current implementation inventory

Implemented and historically proved:

- exact boot-only candidate/rollback machinery and physical recovery;
- fast native boot and automatic handoff control;
- read-only UFS mount, immutable content validation, bounded writable tmpfs;
- native Wi-Fi bring-up/helper health;
- durable no-replay journals and final native health after attended return.

Reviewed in H24 source but not live-proved by its failed D1:

- fresh Debian tmpfs `/dev` and mandatory devpts as a historical starting
  point, but with optional `ttyGS0`, a global console node, and no proved
  private `newinstance`; that exact node/devpts set is rejected here;
- private-card-root HUD path (now removed from the selected direction).

Not implemented for the selected direction:

- native safety supervisor that remains parent of Debian;
- nested Debian PID/mount/IPC/UTS/network namespaces, cgroup boundary, and
  `pivot_root` bootstrap;
- veth/netfilter IP boundary and exact cleanup;
- SD-free bootstrap receipt and native cache evidence transport;
- dedicated native read-only evidence retrieval and attended host
  SSH/workload observer;
- UFS `sda` benchmark telemetry.

## Authority

This document is H0 only. It authorizes no connected read, candidate build,
identity allocation, qualification, approval, flash, reboot, signal, handoff,
UFS mutation, network change, or recovery. Any implementation changes the
execution-critical closure and requires independent review. A future
capability `PASS_GO` qualifies code only; fresh live gates remain mandatory.
