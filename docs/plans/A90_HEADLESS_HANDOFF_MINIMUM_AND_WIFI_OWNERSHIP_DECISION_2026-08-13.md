# A90 headless handoff minimum and Wi-Fi ownership decision

Date: 2026-08-13
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 design
Live authority: none

## Outcome

The project does not need to rewrite the proven UFS qualification and safety
transaction from zero. It needs a smaller product contract around that core
and an explicit Wi-Fi owner before another candidate is allocated.

The selected owner is native. Native PID 1 remains a minimal headless safety
supervisor with the existing native Wi-Fi service. One child becomes Debian
PID 1 in fresh PID, mount, IPC, UTS, and network namespaces, privately mounts and pivots
to the exact UFS appliance, and receives only a reviewed veth/IP path. Debian
owns SSH, logging, the server workload, and any later optional display, but it
does not own or name `wlan0`, native tasks, or native IPC/device state. The
ownership-stop experiment and its replacement atomic diagnostic are retired.

No H26 ordinal, version, profile, state path, artifact, or live runner is
created by this design. Identity allocation follows the Wi-Fi decision so a
failed design does not leave another dead candidate lineage.

## Current implementation inventory

| Area | Current implementation | Evidence status | Product decision |
|---|---|---|---|
| Boot resident | Exact boot-only F1 install, post-tool artifact revalidation, rollback and final native health | H24 installed and healthy | Keep |
| One-shot dispatch | Versioned enable/latch, latch before handoff, consumed-effect no replay | Live-proved in prior lanes | Keep; add compact cache receipt later |
| UFS discovery | Runtime `sda33`/`dev_t`, sector, label, UUID, marker, unmounted and clean-ext4 checks | Reviewed; multiple earlier live boundaries | Keep |
| UFS root | `ro,noload,nosuid,nodev` mount and exact content validation | H24 reached and proved mount/content | Keep |
| Writable runtime | Bounded tmpfs for `/run`, `/tmp`, `/etc/dropbear`, `/var/log` | H24 live-proved | Keep initially |
| Authentication | H24 boot-private `/root/.ssh` tmpfs overlay | H24 live-proved mount stage, not exclusive client-auth or private-key isolation | Replace with a distinct non-login key daemon, one service-home client key/login account, public-key-only Dropbear, and one forced probe |
| Debian `/dev` | Historical H24 design used fresh tmpfs/core nodes plus devpts; selected successor uses exactly null/zero/full/urandom and no PTY | H24 stopped before live execution | Keep only fresh/no-devtmpfs principle; independently prove the reduced no-PTY tree |
| Display cleanup | Bounded scan/release of native DRM owners before mount transition | Earlier live use; shared safety function | Keep until headless proof; remove broad scan only after explicit ownership exists |
| Persistent HUD | Native presenter plus private card root after UFS mount | H24 failed at bootstrap; H25 alternatives retired | Remove from headless path |
| Wi-Fi | Persistent native helper, Android companions and native autoconnect in shared network/PID environment | Earlier functional evidence, but shared proc/network exposure is unproved | Keep native owner; isolate Debian with fresh PID/mount/IPC/UTS/network namespaces plus veth/netfilter |
| USB/NCM | Kernel gadget prepared for Debian; native TCP control is not required in Debian | Earlier observation path | Keep as attended recovery/first-proof channel |
| Same-run evidence | SD evidence-run file bind plus host observer/journal | Works but hard-requires SD | Replace with native cache receipt plus authenticated host observation; no post-exec rootfs writer assumed |
| Failure fallback | Stage/rc/errno attribution, child cleanup, mount restoration, UFS unmount, native continuation | Repeatedly exercised | Keep |
| Persistent terminal | Debian service proof while live, attended return/recovery for final native health | Contracted; earlier lanes exercised variants | Keep states separate |
| Benchmark | `CLOCK_BOOTTIME` stage markers plus CPU/GPU/temp/memory/power and `mmcblk0` sectors | Implemented test instrumentation | Keep host/test-only; correct storage counter for UFS before comparison |
| Rootfs services | Exact immutable H14 UFS demonstration content including Dropbear, smoke, HUD-intent, and Debian Wi-Fi paths | Audited incompatible with the isolated native-Wi-Fi minimum and has no inherited-FD writer | Build and independently review a separately versioned minimal rootfs before the first candidate; installation remains separately authorized |

This table separates "implemented" from "proved in one current run". H24's
failure at persistent HUD means the post-HUD minimal `/dev`, core-mount move,
and `switch_root` steps are reviewed source, not H24 live evidence.

## Absolute production requirements

The following remain even in the smallest build:

1. exact A90 target, installed-resident, candidate, rollback, and recovery
   identity;
2. boot-only transfer and a durable launch journal with candidate no-replay;
3. versioned one-shot handoff intent consumed before the effect;
4. fresh same-boot UFS identity and clean read-only mount proof;
5. exact writable tmpfs set, boot-private SSH authorization, and a read-only
   minimal Debian `/dev` containing only null/zero/full/urandom, with no
   devpts, ptmx, tty, console, physical node, block node, or submount;
6. immediate fail-closed traffic/session ingress block, then exact immutable
   failure stage/rc/errno plus cleanup intent/identities recorded before any
   termination or removal, followed by separately appended bounded child reap,
   mount restoration, UFS unmount, and unchanged-userdata proof;
7. an attended recovery channel independent of Wi-Fi;
8. same-run authenticated proof of Debian namespace PID 1, SSH, root mount,
   minimal `/dev`, and network state;
9. final cable-free Wi-Fi owned by a component whose root, descriptors,
   namespace, credentials, and lifetime are explicitly bounded;
10. `HEALTH_PENDING_PERSISTENT_DEBIAN` while Debian is live and exact
    `RESIDENT_HEALTHY` only after attended return or recovery.

Logging is part of the minimum, but verbose telemetry is not. The target needs
only a compact durable sequence containing intent identity, checkpoint,
boottime, failure stage, rc/errno, cleanup result, and zero-write result. Raw
logs and large observer transcripts stay private on the host.

## Wi-Fi ownership diagnostic disposition

The attempted H24 shell-based W0 is retired without qualification or live
contact. Every installed H24 `cat` and `run` command reaches PID 1's generic
command-boundary orphan reaper, so the proposed inventory was not D0. Its
separate inventory and stop frames also could not atomically preserve the
approved process, group, session, and mount-namespace closure through
`SIGTERM`. The deleted runner and tests are not evidence and are never resumed.

The replacement atomic design in
`A90_ATOMIC_WIFI_OWNERSHIP_DIAGNOSTIC_RESIDENT_DESIGN_2026-08-14.md` is
`NO_GO_RETIRED`. It accumulated a new Binder/AF_UNIX/process-broker runtime and
still could not reproduce H24's distinct post-fork UID/GID/capability roles
without reopening its filter boundary. That is disproportionate for a single
measurement. It grants no identity or live authority and is never implemented.

The selected production direction is
`A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`. It stops trying
to transfer ownership. Native PID 1 retains the exact native Wi-Fi owner and
supervises Debian as PID 1 in separate PID, mount, IPC, UTS, and network namespaces.
Debian receives only a veth/IP boundary, fresh procfs, minimal `/dev`, and the
read-only UFS root. Native tasks, abstract AF_UNIX/Binder/property state,
`wlan0`, old root, device nodes, and native keyrings are not nameable from
Debian. Before `CHILD_READY`, the forked child may only close FDs and exact-
exec one manifest-bound static bootstrap; parent-verified `maps`/`map_files`
must then contain no inherited native anonymous/shared/file/device mapping and
remain bound at every stop. The child procfs is `nosuid,nodev,noexec,hidepid=2`, masks every
non-allowlisted global top-level view including all writable kernel controls,
then is remounted read-only; only child PID/net/IPC/mount views and a finite
service-traced scalar allowlist remain. Keyrings are closed separately from
`CLONE_NEWIPC`: trusted bootstrap
joins a proved-empty anonymous session and one inherited all-ABI static
isolation filter denies keyring calls, `unshare`/`setns`, node creation,
`clone3`, namespace/unknown legacy-clone flags, and every supported
post-bootstrap mount/root API after hiding proc key listings. This prevents a
later user namespace from regaining mount or device capability even on a
kernel that otherwise permits unprivileged user namespaces; the consoleless
PID-1/Dropbear/workload trace must prove its finite fork flags still work.
The same filter permits direct sockets only for exact AF_INET TCP/UDP service
forms and, if traced, an addressless child-local AF_UNIX `socketpair`; direct
AF_UNIX, QRTR, netlink/kobject, packet/raw, Bluetooth, NFC, VSOCK, CAN, XDP,
control families, unknown values, and compat `socketcall` are denied. No socket
FD is inherited.
The bootstrap never calls the get-or-create `KEYCTL_GET_PERSISTENT`; only
already-attached thread/process/session subscriptions are observed with
no-create operations. User and user-session special keyrings are never
resolved because even a `create=0` lookup may instantiate them.

That architecture is H0 and unimplemented. Namespace/veth/netfilter/pivot-root
support, capability drops, keyring/exec-envelope closure, crash-prefix
no-replay, exact network cleanup,
SD-free logging, and performance must receive independent review before a
fresh identity. Missing support is `NO_GO`; shared namespaces are not a
fallback.

The veth policy is not only a FORWARD policy. Before the child peer is
configured or released, native-veth `INPUT` and native `OUTPUT` toward Debian
default to drop, no native TCP/UDP listener is allowed across the peer, and
only a closed non-payload neighbor/control exception may pass. Exact
table/chain/set/rule handles, counters, interface identities, boot nonce, and
removal receipts cover INPUT, OUTPUT, forwarding, and NAT. The sole SSH path is
preinstalled as an exact dormant set/handle with its activation element absent;
it is opened only by the later durable intent/one-shot/readback sequence. Any native-local
reachability or cleanup ambiguity is `NO_GO`/`RECOVERY_PARKED`.

Namespaces do not bound aggregate resource use. Before release, the blocked
child and all future descendants are placed in one exact manifest-frozen cgroup
layout with pids, memory+swap (or proven no swap), CPU, and fresh-UFS-device I/O
limits that preserve explicit native/Wi-Fi/recovery reserves. No controller is
visible inside Debian. The first proof also uses a fresh UTS namespace and
fixed hostname. Every required native IPv4 forwarding/per-interface sysctl is
a compatible read-only precondition: `ip_forward` and existing all/default/wlan
values are never written. Only nonce-created veth and child-netns fields change;
removing the veth restores that new state, while child IPv6 is disabled without
changing native IPv6.

The successor does not retain H24's optional `ttyGS0`, global `/dev/console`
(5:1), shared devpts behavior, or any PTY feature. Its consoleless rootfs
receives exactly `/dev/null`, `zero`, `full`, and read-only-mode `urandom`,
verified `/dev/null` stdio, no controlling tty, and no devpts, ptmx, tty,
`/dev/random`, shm, submount, native/physical character node, or block node.
The complete root `/dev` is final-remounted read-only. Dropbear rejects PTY
requests and the attended proof uses non-PTY SSH.

Before exec, trusted bootstrap creates two non-aliasing manifest-fixed nonzero
identities unused by native tasks and files. The service UID/GID owns PID 1,
the only login account, forced probe, and workload. A distinct locked non-login
SSH-key-daemon UID/GID owns the non-privileged-port Dropbear listener/session
engines and the mode-0700/mode-0400 private-key tree only. Boot-private client
authorization is installed only as a
read-only mode-0600 `authorized_keys` in that service UID's manifest-fixed
home; H24's `/root/.ssh` overlay is not reused. The separately versioned
content manifest binds the exact Dropbear binary/config/argv, account database,
and canonical one-line key grammar. Exactly one nonzero service account and
one boot-private client key are login-eligible. Password, empty-password,
`none`, keyboard-interactive/PAM, root/alternate-account or alternate-key
authentication are disabled; the account has no general shell. One immutable
read-only probe is forced, and arbitrary command/subsystem, PTY, local/remote
forwarding, agent forwarding, and X11 forwarding are rejected. Missing exact
build/parser support is `NO_GO`, not a fallback. One inherited all-ABI static
default-deny filter admits only
the trace-derived positive syscall/argument corpus. It rejects unneeded global
kernel-object allocators, `/dev/random`/`GRND_RANDOM`, queued real-time signals,
and unknown ioctl/fcntl/prctl operations. Cgroup limits are supplemented by an
exact global file-table, pipe, socket, epoll, timer, per-UID and kernel-memory
reserve calculation plus empty-cleanup proof.
The blocked child is also reread as `SCHED_OTHER`, priority 0, nice +10,
`SCHED_RESET_ON_FORK`, one manifest-frozen CPU subset, `IOPRIO_CLASS_BE` 7,
and exact bounded uclamp before release. RT/RR/DEADLINE inheritance, Android
scheduler boosts, and later scheduler/priority/affinity/ioprio/uclamp changes
are fail-closed.

The clean bootstrap first forks one exact static-exec non-dumpable
`RLIMIT_CORE=0` transient generator with a closed FD/stdio/output set, proves
its clean maps and that it exited/reaped with no core/log/temp/private-output
residue, then opens without reading the exact host-key/public/account/
dispatcher objects for one child that immediately clean-execs the static key
daemon. The daemon becomes permanently non-dumpable, applies its fixed filter,
emits `KEY_DAEMON_CLEAN_READY` on its sole transient internal status pipe before
key load/listener bind, then may load and bind only while ingress remains
blocked. It emits `KEY_DAEMON_LISTEN_READY` and closes that pipe before any
accept. The clean bootstrap validates both frames and EOF and alone forwards a
canonical scalar summary; Native PID 1 proves exact maps, map_files, IDs,
capabilities, filter and FDs before `LOCAL_PERSISTENT`; that verification never
opens ingress or permits an accepted connection. The
service UID cannot traverse the key tree or inspect the daemon through proc,
ptrace, process-vm, or pidfd-getfd. The daemon retains only bounded
`CAP_SETUID`/`CAP_SETGID`; its authenticated child may perform only the exact
service-GID/UID transition, then performs an explicit exact zero-`capset`,
ambient clear, and complete capability/saved-ID reread. It never assumes a
nonzero-to-nonzero UID change clears caps. It zeroes every child-side key copy
and execs only the prebound dispatcher. The
dispatcher inherits no key/config/listener FD or private buffer. Missing exact
Dropbear source proof, an aliased UID/GID, a readable daemon proc surface,
retained key material, a generator crash/private output/residue, or identity/
capability regain is `NO_GO`.
Cleanup blocks new sessions, reaps every bound listener/session engine, proves
both dedicated-UID resource sets and all key-daemon PIDs/FDs gone, and only then
destroys the private-key tmpfs.

Cgroup accounting alone cannot bound softirq, skb queues, conntrack memory, or
Wi-Fi airtime. The manifest therefore also freezes parent-owned MTU,
`txqueuelen`, bidirectional packet/byte rate, burst and queue limits on both
veth ends, plus new-flow-rate and maximum concurrent-flow bounds in one
dedicated conntrack zone. No global conntrack scalar, existing Wi-Fi qdisc, or
other interface changes; cleanup removes and verifies only nonce-bound queue,
zone, rule, and interface state.

## Minimal isolated-Debian handoff state machine

```text
native healthy
  -> fresh target/UFS/rollback preflight
  -> prepare recovery USB/NCM
  -> exact native Wi-Fi owner and ordinary cloning-thread scheduler healthy
  -> durable one-shot intent and latch
  -> one inherited-mm close/exec-only child enters the static clean bootstrap
  -> one CHILD_READY child blocked on an empty control pipe
  -> parent pidfd SIGSTOP proves first stop + clean maps + exact two-pipe FD set
  -> exact scheduler plus pids/memory+swap/CPU/UFS-I/O cgroup bounds active
  -> parent moves only the veth peer by netns FD, closes it, proves zero nsfs FD
  -> parent binds native-end/rule policy with no retained namespace handle
  -> durable NETWORK_PREP_INTENT then N token + first pidfd SIGCONT
  -> child configures/rereads its peer, sends no payload, drops CAP_NET_ADMIN
  -> child emits NETWORK_PREPARED and blocks on the empty control pipe
  -> parent pidfd SIGSTOP verifies network frame+stop+capability+FD absence
  -> durable ROOT_PREP_INTENT then R token + second pidfd SIGCONT
  -> child mounts UFS read-only + tmpfs auth/runtime + minimal /dev
  -> child emits ROOT_PREPARED and blocks on the empty control pipe
  -> parent pidfd SIGSTOP verifies root frame+third stop+digests+two-pipe FD set
  -> parent durably records CHILD_RELEASE_INTENT
  -> X/RELEASE token + third/final pidfd SIGCONT
  -> exact dispatch result records CHILD_RELEASED without retry
  -> child pivot_root + old-root detach + isolated key-daemon launch
  -> service capability/UID/filter drop and PID-1 exec
  -> parent observes exact same-pidfd Debian exec; bootstrap pipes are closed
  -> KEY_DAEMON_LOCAL_READY + LOCAL_PERSISTENT with exact SSH gate dormant
  -> durable INGRESS_OPEN_INTENT
  -> one atomic prebound-element activation + exact return/readback
  -> INGRESS_OPEN; every other ingress remains default-drop
  -> attended host pins the server key, authenticates one public key/account,
     and proves the forced read-only probe with no alternate SSH feature
  -> HEALTH_PENDING_PERSISTENT_DEBIAN
  -> attended return/recovery
  -> exact native RESIDENT_HEALTHY
```

Native PID 1 never leaves its namespace. Any failure before child release
first blocks new traffic/session ingress, durably records the immutable
original failure plus cleanup intent and exact bound identities, then reaps the
blocked child, removes only bound zone/queue/veth/rules and empty child cgroups
after proving no parent nsfs descriptor pins a child namespace,
and appends cleanup results separately without overwriting the original
failure. Existing Wi-Fi
counters may advance monotonically but their configuration and identity never
change. Any uncertain post-intent state parks; it does not
resend arm, reboot, candidate transfer, or child launch.

The durable intent is published before the first child or network effect. A
crash after intent but before child creation therefore reconciles as a consumed
no-child prefix; it never creates the child later. No supporting diagram or
implementation may move child creation, veth creation, or netfilter changes in
front of that durable boundary.

The bootstrap has exactly three fixed control tokens and three parent
continuations. The child first emits `CHILD_READY` and blocks on an empty
control pipe; the parent proves the first stop and independently enumerates the
exact two-pipe child FD set before proceeding. The
parent then moves only the veth peer with the bound netns FD while remaining in
the native namespace. It binds the sole close-on-exec FD number/flags/nsfs
inode, proves no duplicate, uses it only in that exact acknowledged move, closes
it immediately, and enumerates zero parent references to the child namespace
before native-end configuration or any continuation. Every later scoped
namespace observation closes its FD and repeats the zero-reference proof before
publication. The one-byte `N` token and first pidfd `SIGCONT` follow
durable `NETWORK_PREP_INTENT`; they permit only child-local peer/address/route/
sysctl/traffic-control setup, exact reread, zero userspace payload, bounded
kernel neighbor/control counters, permanent
`CAP_NET_ADMIN` removal, a unique `NETWORK_PREPARED` frame, and another empty-
pipe block. The parent sends a second pidfd `SIGSTOP` and verifies the frame,
stop, native-side digests, capability absence, and exact two-pipe FD set with
no retained netlink socket. The one-byte `R` token and
second pidfd `SIGCONT` follow durable `ROOT_PREP_INTENT` and permit only private
root/key preparation, a unique `ROOT_PREPARED` frame, and the third empty-pipe
stop barrier. Only after the parent verifies that third stop plus the exact
two-pipe FD set and durably
publishes `CHILD_RELEASE_INTENT` may it send one-byte `X`/`RELEASE` plus the
third/final continuation that permits pivot/exec. Exact successful results for
all three token and signal dispatches publish `CHILD_RELEASED`; a missing
result is uncertain and never retried. An early exec, native `setns`, retained
`CAP_NET_ADMIN`, wrong token/stop/pidfd, missing frame, extra dispatch, or crash
uncertainty is never resumed and becomes exact cleanup or `RECOVERY_PARKED`.

The SSH path is a separate post-exec one-shot effect, not a fourth child-control
token. The pre-release network transaction installs one exact dormant gate and
binds its table/chain/set/rule handles, absent activation element, zero counters,
default-drop prestate, target/boot/run identity, and close-only cleanup. After
`LOCAL_PERSISTENT`, native PID 1 durably publishes `INGRESS_OPEN_INTENT`, inserts
that one element once, then requires exact command return and an independent
handle/element/policy/counter readback before `INGRESS_OPEN`. No host connects
before that record. Missing/torn result, wrong/duplicate handle or element, or
readback drift is never resent; exact-identity cleanup removes only the element,
proves the gate dormant, and parks, while incomplete identity parks without a
global flush. Return closes and proves the gate before child termination.

The first proof does not require sysvinit or firstboot to retain or write an
arbitrary descriptor. Both pipes are created `O_CLOEXEC`; the inherited-mm
branch may clear that flag only on the two child ends for the one clean
bootstrap exec, whose first instructions re-arm it before `CHILD_READY`.
Thereafter the parent-to-child control and child-to-parent receipt pipes remain
close-on-exec: the control pipe carries only the three fixed one-byte
`N`/`R`/`X` opcodes, while the receipt pipe carries only fixed-schema trusted-
bootstrap stages and failures. Native PID 1 records the local
pidfd/exec/network facts; a separate attended host proves SSH and the workload
through the exact IP path only after retrieving the same-run, target-bound
per-boot Ed25519 host-key algorithm, public key, and fingerprint from the
dedicated native read-only receipt and enforcing strict host-key comparison.
TOFU is not evidence. It then uses only the exact fixed service account and
private counterpart; evidence binds the negotiated public-key method, accepted
client-key fingerprint, forced read-only probe, and zero password/interactive/
root/alternate-account/shell/subsystem/PTY/forwarding/agent/X11 path. The exact
public audit rejects the installed
demonstration firstboot because it also starts legacy NCM/smoke/HUD-intent/
Debian-Wi-Fi paths. A separately versioned minimal rootfs is therefore built
and reviewed before the candidate rather than adding an overlay or post-exec
pipe. That minimal content supplies but does not start or own the key daemon;
trusted bootstrap launches it under the distinct non-login identity after
binding the bootstrap-generated server key and remounting the exact
`/etc/dropbear` tmpfs read-only. PID 1, the forced probe, and the workload never
generate, rotate, read, or inherit that key. The content manifest also binds
the public-key-only Dropbear feature matrix,
exact argv, single login account/key, and forced probe, with every other
authentication and session feature fail-closed. Its future UFS installation
remains `NO_GO`
until a separately reviewed
higher-precedence boundary change and distinct attended capability exist.

The two bootstrap pipes are the only native-facing pipes, and the clean
bootstrap is the sole native-receipt writer. Generator and key-daemon helper
forks may only close both main-pipe ends before clean exec and never carry or
write them across that exec. One helper at a time receives one transient internal
`pipe2(O_CLOEXEC)` status writer plus only its manifest-bound object FDs for one
static exec; its first instructions re-arm close-on-exec and reread that exact
FD set. The generator emits exactly `GENERATOR_CLEAN_READY` then public-only
`GENERATOR_PUBLIC_COMPLETE`, closes before exact exit/reap, and reaches EOF.
The daemon emits exactly `KEY_DAEMON_CLEAN_READY` then
`KEY_DAEMON_LISTEN_READY`, closes before any accept, and reaches EOF while it
remains live. Bootstrap binds helper pid/start/pidfd, frame order, byte cap, FD
set and EOF, closes the internal read end, and forwards only one canonical
summary. Wrong or multiple writer, inherited main-pipe end, extra FD,
interleaved/partial/duplicate/extra frame, premature or late EOF, helper crash,
or residue is `RECOVERY_PARKED`; the channel is never replayed.

## Test and benchmark features

Test instrumentation is intentionally outside the production minimum:

- stage timestamps for native start, cache readiness, Wi-Fi boundary, UFS
  mount, writable-set ready, pre-switch, host-observed Debian SSH ready, and
  final network;
- CPU 0/4/7 clock, GPU clock, CPU/GPU/battery temperature, memory/load,
  battery current/voltage, and calculated power sampled at a small fixed set of
  stages rather than continuously;
- storage counters from exact UFS whole device `sda`, not the current
  `mmcblk0`-only counter;
- boot-to-handoff, handoff-to-SSH, handoff-to-Wi-Fi, and steady-state samples;
- target binary size and rootfs manifest size;
- a fixed workload after functional success, then section-GC and Full-LTO as
  separate build comparisons.

Benchmark collection never delays, retries, or changes a handoff decision.
Missing telemetry is `na`; it cannot turn an unsafe or unhealthy run into PASS.
Continuous polling, long trace windows, debugfs, firmware trace, display HUD,
CPU stress, and smoke/tunnel traffic are laboratory features and are absent
from the final production profile.

## Removal schedule

### Remove before the next candidate

- persistent native HUD and all display-success predicates;
- firstboot overlay and boot chime;
- SD evidence bind and compiled SD property-root dependency;
- any shared PID/proc/network namespace that makes native state visible to Debian;
- continuous HUD polling and display presenter artifacts;
- candidate-specific legacy rootfs copy/hash work from the direct-UFS lane.

### Keep for first proof, then reduce

- strict display-owner release;
- detailed stage attribution and private raw logs;
- USB/NCM attended observation;
- separately versioned minimal UFS content completed and reviewed before the
  candidate; the historical demonstration content is not the first-proof root;
- conservative native Wi-Fi and isolated veth/netfilter diagnostics.

### Remove from the formal production image after repeated proof

- formatter/populator and experimental shell commands;
- debugfs and firmware trace;
- long Wi-Fi watcher/supervisor budgets;
- HUD, Doom, stress, smoke HTTP and tunnel binaries/content;
- benchmark emitters beyond a small optional diagnostics build;
- obsolete lineage adapters from the active package, while Git/archive retains
  their evidence.

Host approval, journaling, rollback, recovery, and final-health evaluation are
not target-image bloat and remain.

## Why the implementation became large

The growth was not caused by one slow function. Four concerns accumulated in
the same target and host surfaces:

1. product services: SSH, Wi-Fi, display, HUD, tunnel and smoke checks;
2. safety transaction: target identity, rollback, no-replay, mount restoration
   and terminal health;
3. experiment tooling: SD copying/hashing, UFS population, traces, benchmarks,
   stress and display tests;
4. incident compatibility: each failure added a new parser, marker, observer,
   version branch, and retained historical adapter.

Safety checks should be shared and retained. Product and experiment features
must become separate modules/profiles, and retired adapters should remain
historical rather than ship in init. Compiler optimization comes only after
this ownership and module split; LTO cannot correct an unsafe process model.

## Exit criteria

This design advances to implementation only after an independent H0 review
accepts the retirement and architecture boundary, and host/static feasibility
proves the required PID/mount/IPC/UTS/network namespaces, private procfs, exact
cgroup resource bounds, veth/netfilter operations, `pivot_root`, capability
drops, SD-free evidence, and
exact cleanup. Missing support is `NO_GO`; it does not reactivate an ownership
experiment or permit a shared-namespace fallback. A later candidate needs its
own fresh identity, deterministic boot-only artifacts, capability
qualification, connected D0, attended F1 approval, resident health, separate
attended D1 approval, and same-run result. This H0 document grants none of
those authorities.
