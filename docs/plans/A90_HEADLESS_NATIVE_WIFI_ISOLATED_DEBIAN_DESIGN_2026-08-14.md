# A90 Headless Native-Wi-Fi / Isolated-Debian Design

Date: 2026-08-14
Selected target: Samsung Galaxy A90 5G only
Tier: H0 architecture and feasibility boundary
Status: selected direction; independent H0 review required; no live authority

## Decision

The production successor will not reproduce the retired atomic Wi-Fi ownership
diagnostic. It will keep the already-required native Wi-Fi owner in the native
namespaces and launch Debian as PID 1 of separate PID, mount, and network
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

- native Wi-Fi processes stay in the native PID, mount, IPC, and network
  namespaces;
- Debian sees a fresh procfs, minimal `/dev`, private mount tree, and a veth
  interface in a separate network namespace;
- native Binder, property-service, abstract AF_UNIX, process FDs, old root,
  userdata block devices, and Wi-Fi control interfaces are not nameable from
  Debian;
- the only cross-boundary data planes are IP packets through the reviewed veth
  policy and fixed scalar health/log pipes created before Debian exec.

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
later boot-private authorization and always-fresh minimal Debian `/dev` safety
contracts. It does not carry forward H16/H24's in-place native-PID1 root
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
5. minimal Debian `/dev` plus mandatory devpts, with no block, userdata, DRM,
   native devtmpfs, or inherited directory handle;
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
process, namespace, FD, socket, and driver identities. It then creates exactly
one Debian bootstrap child with `CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWNET`.
The child is PID 1 of the new PID namespace and blocks before any Debian code.

The parent and child prove:

- the child PID namespace differs from native PID 1 and has no native task;
- the child mount namespace is recursively private;
- every inherited procfs, sysfs, devtmpfs, old-root, cwd, and directory FD is
  inventoried before trusted bootstrap and absent after pivot;
- the child network namespace differs from native Wi-Fi's network namespace;
- no native AF_UNIX socket or netlink control socket is visible in the child;
- no unexpected task exists in either the native Wi-Fi set or Debian subtree.

The trusted child bootstrap mounts one procfs associated with its own PID
namespace, mounts a deliberately bounded read-only sysfs view, constructs a
fresh tmpfs `/dev`, mounts devpts, and prepares UFS in its private mount
namespace. It validates the immutable UFS content, writable tmpfs set, and
Debian init before pivot. It uses `pivot_root`, changes cwd to `/`, detaches and
removes the old root, closes every bootstrap FD, proves the exact post-pivot
root/mount/FD tree, drops bootstrap capabilities, and only then execs Debian
init. `chroot` alone is forbidden.

Debian PID 1 and every descendant remain inside that PID namespace. The native
supervisor is absent from Debian `/proc`, and Debian has no `/proc/<native-pid>`
route to a native root, FD, namespace, or device capability.

## Network boundary

The namespaces never share AF_UNIX or netlink control state. The native side
keeps `wlan0` and its exact helper. During the blocked bootstrap, native code
creates one veth pair through a reviewed rtnetlink implementation, moves only
the Debian peer into the child network namespace, and binds both interface
identities by ifindex, namespace inode, and boot nonce. No general `ip`, shell,
or host-provided command is used.

The native supervisor installs a closed forwarding policy through a reviewed
netfilter interface:

- default drop in both forwarding directions;
- established/related return traffic only;
- outbound TCP/UDP from the Debian veth subject to exact egress policy;
- the single selected inbound server port forwarded to a non-privileged
  Debian listener;
- no forwarding to native management, Binder/property sockets, USB, loopback,
  link-local control, or other device interfaces;
- exact rule handles, counters, boot nonce, and removal receipt.

Concrete addresses and device-private network values are generated or loaded
from boot-private state and remain under `workspace/private/`; none enters the
tracked manifest, report, or log. DNS input is materialized in a bounded
Debian tmpfs file from boot-private configuration, never an SD property root.

Before Debian exec, the bootstrap drops `CAP_NET_ADMIN`, `CAP_NET_RAW`,
`CAP_SYS_ADMIN`, `CAP_SYS_PTRACE`, `CAP_MKNOD`, and every capability not in the
reviewed server minimum from the permitted/effective/inheritable/ambient and
bounding sets. The selected server binds a non-privileged internal port, so it
does not need `CAP_NET_BIND_SERVICE`. No Debian process can move `wlan0`, alter
routes/rules, open raw packet sockets, or enter a native namespace.

Kernel support for PID/mount/network namespaces, veth, the exact netfilter
operations, per-namespace procfs, and capability bounding is a host/build plus
unarmed boot self-check gate. Missing support is `NO_GO`; neither a shared
network namespace nor a userspace proxy is an allowed fallback.

## Handoff state machine

All records are private regular mode-0600 files published temp-fsync,
atomic-no-replace, and directory-fsync. Existing, linked, wrong-mode, torn, or
extra members fail closed.

1. `BOOT_HEALTHY`: exact resident self-test, rollback, recovery, Wi-Fi, UFS,
   content, and boot-private inputs validate while unarmed.
2. `HANDOFF_INTENT`: bind boot generation, candidate identity, UFS identity,
   native Wi-Fi health, namespace/network plan, and maximum one child launch.
3. `CHILD_BLOCKED`: clone exactly one bootstrap child and bind PID/start time,
   pidfd, namespace inodes, and initial stopped state.
4. `NETWORK_READY`: create/bind veth and exact forwarding rules; require zero
   packets before child release except reviewed neighbor/control setup.
5. `ROOT_READY`: child privately mounts and validates UFS, writable tmpfs,
   procfs/sysfs/minimal-dev, Debian init, and old-root removal plan.
6. `CHILD_RELEASED`: durably record the one release before allowing pivot/exec.
   A crash after this point never launches a second child.
7. `DEBIAN_EXEC`: child publishes fixed scalar pre-exec and post-exec receipts;
   parent proves the same pidfd now names exact Debian PID 1.
8. `SERVICE_READY`: Debian reports authenticated SSH and workload health over a
   one-way fixed-schema pipe; parent combines that with native Wi-Fi, veth,
   forwarding, mount, and namespace observations.
9. `PERSISTENT`: publish `HEALTH_PENDING_PERSISTENT_DEBIAN`; parent enters a
   bounded supervisor loop and never claims final resident health.
10. `RETURN`: attended reboot or failure cleanup terminates the exact Debian
    PID namespace, removes only bound network rules/interfaces, proves the
    child mount namespace gone, and verifies exact native health before
    `RESIDENT_HEALTHY`.

No stage resends candidate transfer, launches another Debian child, or applies
network rules twice. Crash reconciliation reads the durable stage and current
pidfd/namespace/rule identities. Ambiguity parks for attended recovery.

## Logging and evidence

The SD card is not a runtime dependency. Native PID 1 writes compact bounded
records under an exact cache-backed evidence directory. Debian receives no
write handle to that directory. Two one-way `pipe2(O_CLOEXEC)` channels carry:

- fixed-schema lifecycle/health records from Debian bootstrap/PID 1 to native;
- bounded stdout/stderr log frames with sequence, stream, length, and checksum.

The native reader rejects unknown frames, caps total bytes and rate, and writes
append-only chunks plus a terminal digest. Pipes never carry FDs; ancillary
data and AF_UNIX transport are absent. Both pipes are created close-on-exec;
after FD sanitization the bootstrap duplicates only the two child write ends to
reviewed fixed descriptor numbers, clears close-on-exec on those duplicates,
and closes every original or extra endpoint. Debian init receives no read end.
Its exact first service writes the post-exec health frame and never treats the
descriptors as a general command channel. Full raw logs remain private and are
not committed. A later exact read-only status/retrieval path may export only
the bounded redacted result required by the target contract.

Required stage stamps use `CLOCK_BOOTTIME`: resident ready, Wi-Fi ready, intent,
clone, network ready, UFS mount/validation, pivot, Debian exec, SSH ready, and
failure/fallback. Missing telemetry is `na`, never a safety failure unless the
timestamp is itself the required transition receipt.

## Failure and fallback

Because native PID 1 never leaves its root/namespace, failure does not require a
reverse `switch_root`:

- before `CHILD_RELEASED`, kill/reap the blocked child, remove only exact veth/
  rules, let its private mount namespace disappear, record failure, and resume
  the native recovery surface;
- after release but before persistent health, terminate the exact child PID
  namespace, prove every member gone, remove exact network state, and restore
  the native recovery surface;
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
- veth/netfilter boundary, SSH/workload health, compact evidence;
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

- prove kernel/toolchain support for all namespaces, veth, exact rtnetlink and
  netfilter operations, pidfd/wait semantics, pivot_root, and capability drops;
- compile/link the minimal profile and prove HUD/W0/SD code unreachable;
- negative tests for inherited procfs/old-root/dev/FD, native task visibility,
  shared AF_UNIX/netlink, wrong namespace/ifindex, extra forwarding rule,
  capability retention, child replay, torn journal, and cleanup ambiguity;
- crash-prefix tests for every state-machine boundary;
- source/size decomposition review if native additions exceed 900 nonblank
  lines or the host runner exceeds 700 nonblank lines.

Fresh unarmed boot self-check, later under a separately qualified F1:

- create and destroy the exact namespaces/veth/rules without UFS or Debian
  exec, prove full restoration, and store a boot-origin immutable receipt;
- never rerun or overwrite that boot receipt through a manual command.

Only after those pass may a fresh successor identity, manifest, qualification,
and attended F1/D1 process be proposed. This H0 design itself grants none.

## Current implementation inventory

Implemented and historically proved:

- exact boot-only candidate/rollback machinery and physical recovery;
- fast native boot and automatic handoff control;
- read-only UFS mount, immutable content validation, bounded writable tmpfs;
- native Wi-Fi bring-up/helper health;
- durable no-replay journals and final native health after attended return.

Reviewed in H24 source but not live-proved by its failed D1:

- minimal Debian tmpfs `/dev` and mandatory devpts;
- private-card-root HUD path (now removed from the selected direction).

Not implemented for the selected direction:

- native safety supervisor that remains parent of Debian;
- nested Debian PID/mount/network namespaces and `pivot_root` bootstrap;
- veth/netfilter IP boundary and exact cleanup;
- SD-free scalar log/evidence transport;
- isolated Debian SSH/workload health observer;
- UFS `sda` benchmark telemetry.

## Authority

This document is H0 only. It authorizes no connected read, candidate build,
identity allocation, qualification, approval, flash, reboot, signal, handoff,
UFS mutation, network change, or recovery. Any implementation changes the
execution-critical closure and requires independent review. A future
capability `PASS_GO` qualifies code only; fresh live gates remain mandatory.
