# A90 Atomic Wi-Fi Ownership Diagnostic Resident Design

Date: 2026-08-14
Selected target: Samsung Galaxy A90 5G only
Tier: H0 design and contract boundary
Status: `NO_GO_RETIRED`; historical rejected design only; no live authority

> **Retirement boundary:** No code, candidate identity, manifest, approval,
> command, or experiment may be derived from this document. The detailed
> machinery below is preserved only to explain why the ownership-test approach
> was rejected. The selected successor direction is the smaller native-Wi-Fi /
> isolated-Debian design in
> `A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`.

## Outcome

The installed H24 resident remains the exact healthy starting resident, but it
is not a safe execution surface for the Wi-Fi ownership experiment. The
discarded shell prototype split process inventory and `SIGTERM` across
multiple commands, and every H24 `cat` or `run` command reaches the generic
PID-1 command-boundary orphan reaper. That makes the proposed inventory
mutating rather than D0 and leaves an uncloseable process/namespace race before
the signal.

The attempted replacement diagnostic is retired. Successive independent
reviews closed several process, no-replay, PID-reuse, terminal-retrieval,
capability-laundering, Binder, AF_UNIX, and procfs defects, but the resulting
launcher contract is incompatible with the frozen H24 service set. H24 applies
different UID/GID/capability identities after fork and before exec; the draft's
post-filter credential prohibition cannot reproduce those identities. Adding
per-identity trusted brokers, filters, and FD handoffs would create a new IPC
security runtime merely to run one measurement and would defeat the production
reduction objective. This is a design-level `NO_GO`, not an implementation TODO.

No ordinal, version, build string, enable/latch path, artifact, approval, or
live command is allocated by this document. H24 is not patched or replayed.

## Non-permanent gate

Gate: `A90_WIFI_OWNERSHIP_ATOMICITY_GATE_V1`

- Hazard classes: `H24_COMMAND_BOUNDARY_REAPER_EFFECT` and
  `WIFI_HELPER_SPLIT_INVENTORY_STOP_TOCTOU`.
- Scope: every A90 Wi-Fi ownership experiment that inventories or stops the
  installed native Wi-Fi helper before a future headless handoff.
- Blocked paths: the retired H24 shell W0 runner, ad-hoc `cat`/`run` inventory,
  separate inventory and stop frames, and any reuse of its absent approval or
  evidence.
- Retirement evidence: either a different ownership design receives a fresh
  independent review and exact live closure, or the selected production
  successor proves native Wi-Fi and Debian are isolated by separate PID,
  mount, procfs, and network namespaces with no ownership-stop transaction.
- Review trigger: any change to those execution-critical bytes, command
  framing, process selection, bridge identity/locking, journal publication,
  stop/cleanup semantics, recovery, or a new incident invalidates the review.

This retired diagnostic can never satisfy the gate. Every ownership-stop path
remains blocked. The gate is irrelevant only after the selected isolated-
Debian production lane is independently proved to invoke no ownership stop;
it grants no D0, D1, F1, candidate, or recovery authority itself.

## Initial independent review and disposition

The first independent review returned `NO_GO_H0_DESIGN`. It found four
execution-boundary defects in the earlier frozen draft:

1. a helper descendant could escape the selected relationship before the final
   stable snapshot and be laundered into an already-running system baseline;
2. cleanup was proved only before sampling, so a late or restarted survivor
   could outlive the terminal;
3. a final PID check followed by `kill` did not structurally prevent PID reuse;
4. status returned only a terminal hash, so host loss could make the committed
   terminal or intermediate stage evidence unreconstructable.

This revision answers those findings with a stable pre-helper global baseline,
an unreaped direct-child broker plus a nested fresh PID-namespace init, full
post-sample process and namespace accounting, and a status envelope that
returns the complete immutable terminal or every committed stage receipt. The
old review is not a qualification and the revised closure requires a new clean
independent review.

A later clean-rereview checkpoint found one further `HIGH`: unchanged task,
root, and namespace identities did not exclude a helper transferring an open
file, namespace handle, socket, ptrace write, or persistent IPC capability into
an already-baselined process. That closure was also discarded. This revision
therefore permits exactly one pre-helper user-space task, native PID 1, binds
its complete stable FD and credential state, gives the descendant tree no
descriptor-passing or ancestor-inspection channel, and requires the exact
parent state again after cleanup. That finding also requires a fresh review;
the checkpoint itself grants no qualification.

The next checkpoint found two more fail-closed requirements: the parent must
prove `SIGCHLD` cannot auto-reap through `SIG_IGN` or `SA_NOCLDWAIT`, and an
unaccepted-send result must prove the whole one-use ledger pristine rather than
only the requested nonce absent. Those requirements are now explicit. Each
superseded checkpoint closure is invalid and unsigned.

## Diagnostic resident profile

The diagnostic resident is a fresh boot-only successor to H24 with automatic
Debian handoff disabled. Its job is to answer one ownership question and then
return to a known resident state through a separate reboot.

It keeps only what the experiment needs:

- exact A90 target/profile and boot-only rollback machinery;
- the exact H24 Wi-Fi hardware-ready outcome and only the frozen helper/vendor
  binaries required to reproduce it inside the new containment boundary;
- a minimal framed diagnostic control protocol and exact target bridge;
- compact durable cache state for the diagnostic transaction;
- physical Download/TWRP recovery.

Before any Wi-Fi helper exists, the diagnostic profile permits exactly one
user-space task: native PID 1. PID 1 finishes initialization, closes every
nonessential descriptor and IPC endpoint, takes two byte-identical bounded
global process snapshots and two byte-identical `/proc/self/fd`, credential,
root, cwd, umask, and namespace snapshots, and records that closed boot
baseline. Each FD is bound by number, type, flags, device/inode or exact kernel
object identity, and a redacted target class. Every later scan must prove PID 1
retains the same baseline state plus only explicitly phase-owned temporary FDs.
From that point until the ownership terminal, the profile permits no new
process except the sole Wi-Fi supervisor and descendants created beneath it;
the three dedicated verbs execute in PID 1 without forking a command worker.
The trusted supervisor/broker is native PID 1's direct child in the native PID
namespace. Before it forks anything it becomes non-dumpable, closes all
unbound inherited FDs, creates the private mount and IPC containment, and uses
`unshare(CLONE_NEWPID)` so its sole blocked vendor launcher is PID 1 of a fresh
descendant PID namespace. The broker remains outside that namespace and is not
addressable through its freshly mounted procfs.
Every modem/Wi-Fi/Android companion used by the experiment must be created by
that filtered launcher after containment exists; the profile never adopts or
reuses a pre-existing Android helper. A child may fork, reparent, change
group/session, or create a nested namespace, but it cannot join an ancestor PID
namespace. The launcher remains the descendant namespace init; when it exits
the kernel terminates remaining namespace members, and the broker exact-waits
that launcher before restoring containment and exiting.

The global accounting covers every user-space task visible to native PID 1.
Only a task proved kernel-only by the exact frozen kernel-thread predicate may
be excluded; a missing executable alone is not that proof. New kernel workers
are recorded separately but cannot satisfy or hide a helper identity. Any
unreadable or unclassified live task fails closed.

The trusted broker bootstrap creates a private mount namespace. The blocked
launcher detaches every inherited procfs/old-root path, mounts exactly one
procfs for its descendant PID namespace, and proves through exact mountinfo
and negative path scans that the broker and native PID 1 are absent and no
alternate procfs or root handle remains. The broker closes every inherited
descriptor except exact parent `pipe2(O_CLOEXEC)` control/status endpoints and
phase-owned containment/listener/pidfds; the launcher inherits only the exact
pre-bound property FD and scalar handshake/status pipes, closes each handshake
endpoint immediately after its one phase, and only then launches vendor code.
Pipes carry fixed scalar records and cannot carry FDs. The vendor subtree
receives no inherited or global
Unix-domain socket, shared-memory object, writable procfs, native binder
device, or PID 1 endpoint. The private exceptions below are phase-owned
descendant objects, not inherited/global endpoints.

H24's service-object-visible bring-up requires service managers and Binder, so
this design does not pretend it is binder-free. Namespace init mounts a fresh
private binderfs inside its private mount namespace, creates exactly private
`binder`, `hwbinder`, and `vndbinder` devices there, and exposes those nodes
only to the descendant tree. The bootstrap also creates a fresh IPC namespace,
private tmpfs `/dev/socket` and shared-memory locations, and the exact private
AF_UNIX `property_service` shim required by the H24-equivalent path. Every
service/hw/vnd service manager, Binder client, property shim, socket peer, and
shared-memory user is a scanned descendant. Native PID 1 never opens a Binder
device, Unix socket, or shared-memory endpoint and accepts no ancillary
endpoint; the trusted broker is the sole phase-owned direct child.
Pre/post cleanup binds every private mount and IPC endpoint, all Binder FDs and
service-manager identities, requires every reference gone, and proves the
mount/PID/IPC namespaces are destroyed. Using global native Binder, a global
Unix socket or IPC object, passing `SCM_RIGHTS`, or leaving an unobservable
reference is `NO_PROOF`.

The helper must share the native network namespace to observe the same
`wlan0`, so mount and IPC namespaces do not contain abstract AF_UNIX names.
Before helper creation, PID 1 records two byte-identical bounded canonical
snapshots of `/proc/net/unix` and the complete user-task FD-to-socket map. The
only permitted additions are the exact filesystem-path property socket on the
private tmpfs and explicitly enumerated unnamed descendant-only endpoints.
The invariant is **zero abstract AF_UNIX**: a leading-NUL address, a new
unattributed socket inode, or a reference from a baseline task fails closed.

The trusted broker creates, binds, and listens on the exact filesystem
`/dev/socket/property_service` socket before vendor code and passes its bound
FD only to the exact private shim. If the qualified property protocol needs
peer credentials, the broker enables `SO_PASSCRED` only after that socket is
proved filesystem-bound; the setting and bound pathname are reread before FD
inheritance. It remains the unfiltered supervisor/broker and forks one
otherwise blocked, single-threaded vendor launcher. Before installing any
filter, that trusted launcher sets and proves `PR_SET_DUMPABLE(0)`. It then
installs the inherited seccomp user-notification filter with `NEW_LISTENER`,
reports only its listener descriptor number over the scalar pipe, and remains
stopped. While no vendor process exists, the broker opens a pidfd for that
unreaped child, uses its bootstrap-only `CAP_SYS_PTRACE` to obtain the listener
with `pidfd_getfd`, proves the exact anonymous-inode listener identity, and
closes every unrelated pidfd. The launcher closes its listener copy; the
broker irrevocably drops `CAP_SYS_PTRACE`, revalidates its exact capability/FD
state, and only then acknowledges the launcher. No listener or other FD is
sent through the pipe or `SCM_RIGHTS`, and the unfiltered broker cannot
self-notify or deadlock on its emulation syscalls.

Before `NEW_LISTENER`, the launcher also drops and proves every capability not
in its fixed minimal-init set, including `CAP_SYS_PTRACE` and `CAP_SYS_ADMIN`.
The non-dumpable filtered launcher remains the trusted minimal PID-namespace
init and never execs vendor code. After acknowledgement it forks a fixed child
stub for each service/vendor program. A direct BPF argument rule allows only
`PR_SET_DUMPABLE(1)` for filtered tasks; it never creates a notification or
uses `CONTINUE`. The trusted stub performs that call, then
execs one bound non-setuid, no-file-capability executable. It rejects
`PR_SET_DUMPABLE(0)`, credential/capability changes, and setuid/file-capability
exec outcomes; `PR_SET_PTRACER` and equivalent proc-access relaxations are also
denied. Thus every socket-using vendor tracee remains same-credential and
dumpable to the outside broker. The launcher retains no trusted broker/parent pipe or pidfd; its
remaining fixed status channel is untrusted input whose complete frame is
validated by the broker. Thus filtered vendor descendants cannot open or
duplicate `/proc/1/mem`, `fd`, `fdinfo`, `ns`, `root`, `cwd`, `exe`,
`map_files`, or equivalent magic links, while their own dumpable socket-using
processes remain inspectable only by the outside ancestor broker. Any kernel or
LSM behavior that permits a vendor process to access launcher-sensitive procfs
or prevents broker-only tracee inspection is NO_GO at boot self-check.

Every filtered descendant `bind`, `connect`, `setsockopt`, `sendto`, `sendmsg`,
`sendmmsg`, `recvmsg`, and `recvmmsg` is denied or synchronously emulated by
that broker for the exact reviewed syscall corpus; `io_uring` is unavailable.
The filter rejects an unknown audit architecture and covers both AArch64 and
every enabled compat-AArch32 socket syscall number. On an AF_UNIX FD, every
`SO_PASSCRED` request is denied before the kernel can act, regardless of value;
all other socket options need an exact non-address-creating allowlist and are
emulated rather than continued. A `bind` with only `sa_family_t`, any empty or
leading-NUL address, and every other implicit-autobind form is rejected. If the
frozen syscall corpus reveals another autobind trigger, the capability is
infeasible until the filter and this review closure rotate. The broker
duplicates the tracee socket with
`pidfd_getfd`, copies each bounded argument once, rejects `SCM_RIGHTS`, unnamed
or leading-NUL destinations and every AF_UNIX path other than the exact private
property socket, then performs the operation on the duplicate inside the same
private mount namespace and returns the exact result. It never uses seccomp
notification `CONTINUE`, so a tracee cannot swap an FD or pointed-to address
after validation. Vendor code may not bind any socket; it receives the
pre-bound property-service FD. Unsupported address-bearing syscalls or message
layouts fail closed.

Pre-signal, pre-sample, post-sample, and final cleanup repeat the global
`/proc/net/unix` plus FD-reference accounting. The final state must equal the
pre-helper baseline exactly, with the property and unnamed descendant sockets
gone. Kernel support for a new-listener filter, `pidfd_getfd`, bounded tracee
copy, and exact syscall-result emulation is a build/boot feasibility gate;
classic seccomp or an inspect-then-`CONTINUE` fallback is forbidden. This
pre-execution mediation, not periodic sampling, continuously enforces zero
abstract AF_UNIX; the global scans independently detect implementation drift.
Listener
handoff, child blocking, notification cancellation, broker exit, or identity
ambiguity before terminal publication is `NO_PROOF` and recovery-parks the
current boot after any possible signal attempt.

Before launching vendor code, the filtered launcher and every vendor
descendant drop `CAP_SYS_PTRACE`, `CAP_SYS_ADMIN`, and every capability outside
the reviewed Wi-Fi minimum and set no-new-privileges. The trusted broker uses
`CAP_SYS_PTRACE` only in the pre-vendor listener-acquisition phase above, has no
untrusted input or ancestor-access syscall path in that phase, then drops it
irrevocably before acknowledging the launcher. Native PID 1 and the broker are
non-dumpable before launcher creation. Every later filtered tracee stays same-
real-credential and dumpable only to its exact ancestor broker. Exact same-
credential parent `PTRACE_MODE_ATTACH_REALCREDS` checks must allow later
broker `pidfd_getfd` without a capability, while native PID 1 remains
inaccessible because it is non-dumpable and the broker no longer has an
override. Vendor procfs cannot
name either ancestor; no ancestor pidfd, namespace handle, or broker FD is
inherited. If the kernel/LSM cannot prove this asymmetric access model, the
profile is infeasible. The filter rejects
ptrace/process-vm, pidfd-getfd, handle-open, `SCM_RIGHTS`, user-namespace,
BPF/keyring, IPC-namespace creation after bootstrap, mount changes after
private setup, and other cross-namespace persistent-capability creation while
permitting only reviewed private Binder, AF_UNIX, and shared-memory operations
inside the fresh namespaces. Native PID 1 and the broker are non-dumpable for the full helper
lifetime. The new profile must independently prove the same exact
`wlan0`/driver and helper-health outcome as H24 without network sends. If
private binderfs, that hardware-ready equivalence, or the exact restricted
policy cannot be proved, the diagnostic profile is infeasible and fails
review; it does not widen the policy at runtime. Both cleanup proofs require
the launcher/listener and every vendor PID gone and the broker's exact original
FD/capability/non-dumpable state before the broker restores mounts and exits.

The diagnostic parent is single-threaded across the effect and has no SIGCHLD
handler or alternate wait path. At boot and before every identity, signal, and
cleanup boundary it proves `SIGCHLD` has exact default disposition, is not
`SIG_IGN`, has no `SA_NOCLDWAIT`, and is unblocked; no profile code may change
those facts while the child exists. Before the effect it opens one native-only
`O_CLOEXEC` descriptor for the launcher's fresh PID namespace and binds its
`fstat` identity; the descriptor is never inherited by a helper or exposed to
Debian. It deliberately leaves the direct supervisor/broker unreaped from final
identity validation through signalling and all kernel samples. Therefore an
exited child remains a zombie and its outer PID cannot be reused in the signal
window. If fresh PID-namespace creation, the namespace descriptor proof, or
this exact parent/reap/disposition model is unavailable, the diagnostic build
or boot self-check fails closed; it does not fall back to the shared H24 process
model.
The parent accepts no ancillary data and never opens a path named by the child.
Its only helper input is the fixed-size scalar status pipe, validated before it
can affect state. The final capability claim therefore depends on both process
absence and restoration of the exact PID 1 FD/credential/root/cwd/namespace
baseline, not on process identity alone.

It does not execute or claim:

- UFS mount, Debian `switch_root`, handoff latch, or Debian service health;
- persistent native HUD, firstboot overlay, boot chime, or display success;
- association replay, DHCP, DNS, socket traffic, or an external probe;
- SD evidence or a removable-media dependency;
- the general `cat`/`run` shell surface or a host-provided script as the
  ownership transaction.

## H24-to-diagnostic transition

H24 has no command-triggered read path that can now be called pure D0: its
interactive loop invokes the generic orphan reaper before the prompt and after
each dispatched command. The diagnostic F1 preparation therefore must not send
an H24 shell command while claiming connected read-only authority.

Host preparation may use the exact durable H24 install/D1 terminal, immutable
candidate and rollback bytes, operator-attended physical recovery, and passive
host USB endpoint identity. If the independently reviewed F1 implementation
still needs a live H24 version/health command, the fresh F1 approval must bind
the exact bounded pre-transfer command sequence and its known generic-reaper
behavior as F1 preflight control. It runs only after approval, stops before any
transfer on an unexpected receipt or target, and is never reported as D0. The
implementation review must decide whether that exception is needed; this H0
design does not authorize it.

Once the diagnostic resident is installed and healthy, its dedicated status
verb is the only connected read-only surface used by the ownership lane.

## Command surface

The exact protocol verb names remain implementation details, but the qualified
surface has exactly three roles. The diagnostic profile does not route them
through the general interactive shell. Its parser recognizes only the exact
framed status, ownership, and recovery verbs before any generic shell-prompt or
command-end cleanup; arbitrary shell input and the H24 `cat`/`run` surface are
absent.
Ordinary resident profiles remain outside this diagnostic capability and must
retain their compiled bindings and behavior under regression tests.

### Read-only status

The status command is a bounded native reader. Its dedicated dispatcher must
perform no prompt, command-end, orphan-reaper, service, mount, network, or file
mutation. A flag added only after general shell dispatch is insufficient,
because the H24 shell also reaps before reading the next command.

The status command reports one framed, versioned receipt containing:

- exact diagnostic resident/build identity and hashed boot generation;
- auto-handoff disabled and no ownership transaction armed;
- closed pre-helper baseline digest, containment mode, direct-child identity,
  held PID-namespace identity, and current PID 1 FD/credential-state digest;
- direct supervisor/broker and nested launcher PID/start-time/executable
  identities plus current helper health;
- redacted `wlan0` presence, operstate, carrier if readable, and driver
  identity; and
- current transaction state; and
- either the complete immutable terminal envelope or every committed intent,
  signal, cleanup, sample, and failure-stage receipt needed to reconstruct a
  nonterminal state after host loss. Each response uses compile-time-bounded,
  ordered chunks with a whole-envelope size and SHA-256. Missing, duplicate,
  reordered, over-limit, or hash-mismatched chunks are `NO_PROOF`.

It never prints a device serial, MAC, BSSID, IP, credential, PARTUUID, or raw
private path. Read or parse ambiguity is `NO_PROOF`; it is never normalized to
absence.

### Atomic attended transaction

The effect command is a separate verb in the same dedicated dispatcher. It
accepts only the exact compiled capability and a fresh approval-binding digest.
It performs one bounded state machine inside PID 1; no host-provided shell
body, PID list, path, or signal number is accepted.

Acceptance itself is the first no-clobber persistent stage receipt. It binds
the fresh transaction nonce, approval digest, boot generation, and an
accept-count maximum of one before discovery begins. Status always reports the
complete one-use acceptance ledger: exact accepted nonce/digest/count, or a
pristine zero-count ledger with no accepted nonce of any value. A received
transaction is never made retryable merely because later device intent was not
reached.

The command is one D1 effect. It must never be classified or prepared as D0.
The generic orphan reaper is not invoked before or after it; bounded cleanup is
part of the qualified transaction itself so unrelated PID-1 children are not
mutated.

Every phase uses bounded nonblocking or deadline-controlled observation. A
timeout records its exact stage and returns control to the dedicated dispatcher;
there is no unbounded child wait, procfs walk, sleep, or blocking transport read
that can permanently prevent later status retrieval.

### Recovery arm and reboot

The third verb is a separate attended D1 action, available only in exact
`RECOVERY_PARKED`. It accepts a fresh recovery-approval digest bound to the
installed diagnostic build, prior ownership intent and committed receipts,
current boot generation, physical recovery, and one reboot. It durably
publishes a no-clobber recovery intent and then dispatches one reboot. It never
reruns the ownership transaction or starts the helper in the same boot.

Its host runner uses its own durable no-replay journal and holds one exact
bridge-generation lease across target validation, host recovery intent, the
single recovery send, and framing. A durable host recovery intent with an
uncertain response is observation-only: status is retried, but the recovery
verb is never resent.

If reboot returns, native code cancels only that exact recovery marker, fsyncs
the directory, records failure, and requires a new recovery approval; it never
automatically retries. If response is lost after durable recovery intent, host
reconciliation uses status and never resends the verb.

## Native transaction state machine

The phases below are monotonic and recorded in the native durable receipt.

1. **Containment preflight.** Require the exact diagnostic build, boot
   generation, capability, disabled handoff, unconsumed transaction state,
   helper ready/health/result identities, shared native network namespace,
   private helper mount namespace, exact `wlan0`, exact driver, and the stable
   global AF_UNIX baseline with zero abstract address. Prove the non-dumpable
   supervisor/broker is the unreaped direct child of native PID 1, and prove
   its sole filtered launcher is the broker's direct child and PID 1 in the
   fresh namespace matching the held descriptor. Bind both exact outer
   PID/start-time/executable identities. Revalidate the two-scan pre-helper process,
   PID-1 FD, credential, root, cwd, umask, and namespace baseline and
   prove every post-baseline process is in the broker subtree and every
   untrusted member is below the filtered launcher in its PID namespace;
   the profile has no post-baseline process allowlist. Require physical
   recovery to be host-bound; the device command grants none.
2. **Capability snapshot A.** Enumerate the complete supervisor subtree from
   the outer PID namespace and bind every stable
   PID/start-time/PPID/PGID/SID/executable/PID/mount/network-namespace identity.
   Cross-check every current process and the complete parent state against the
   pre-helper baseline plus the exact phase-owned FD set. Kernel
   threads and zombies have explicit
   representations; live `/proc` errors, depth/capacity exhaustion, malformed
   stat data, an unknown post-baseline process, or an unstable scan fails.
3. **Capability snapshot B.** Repeat until two consecutive canonical subtree
   and global-accounting snapshots are byte-identical within a fixed attempt
   and time bound. Reparent, setsid/setpgid, mount/PID namespace creation, and
   late fork remain inside the broker/launcher subtree rather than becoming
   baseline. Volatile scheduler state, health sequence, carrier, and operstate
   are observations, not stable identity. A zombie in the selected closure is
   a failure.
4. **Device intent.** Publish one no-clobber intent by writing a private
   temporary regular file, fsyncing it, atomically publishing it, and fsyncing
   the directory. It binds the boot generation, approval digest, pre-helper
   process and parent-state baselines, both capability snapshots, helper
   result/health
   digests, driver, and maximum signal-attempt/accepted counts of one. A partial
   or unexpected member is not intent proof.
5. **Final revalidation.** Recompute the full snapshot and all stable
   result/health/namespace/driver facts plus the parent FD and credential state.
   Require exact equality with the intent binding. Recheck the broker's direct-
   child relationship/non-zombie/identity plus launcher direct-
   child/PID-namespace-init identity as the final operations before signalling.
   Re-read
   and require exact default `SIGCHLD` disposition with no `SIG_IGN` or
   `SA_NOCLDWAIT` immediately before the signal. The single-threaded parent then
   executes no wait or disposition-changing path before the signal. Drift
   publishes an exact pre-signal cancellation with signal-attempt count zero
   and terminal `NO_PROOF`.
6. **Single effect.** Attempt exactly one `SIGTERM` to the bound, deliberately
   unreaped direct child. Never signal a caller-supplied PID, process group,
   session, or descendant. Because no wait can occur, exit between the final
   check and `kill` leaves the same PID as a zombie and cannot redirect the
   signal to a reused process. Durably record attempt count, return, errno, and
   whether the kernel accepted it. Any attempt or uncertain return consumes
   the transaction and requires recovery, even if `kill` reports failure.
7. **Pre-sample cleanup proof.** Observe the supervisor/broker's qualified
   signal cleanup and exit using exact `waitid(..., WNOWAIT)` or an equivalent
   non-reaping check. Keep the broker unreaped. Require it already exact-waited
   the launcher, require no live process in the launcher's PID-namespace tree,
   and require no unexpected post-baseline process. Prove no
   unapproved persistent IPC/kernel object and exact PID 1 baseline state apart
   from the held namespace FD. The
   kernel's descendant-namespace-init exit rule and global accounting jointly
   close fork/reparent/group/session/nested-namespace escape. Live procfs
   errors, PID ambiguity, an unexpected process, timeout, a launcher that was
   not exact-waited, or a broker that remains live is `NO_PROOF`; no broad
   reaper is used.
8. **Kernel observation.** With the direct broker still an unreaped zombie,
   take ten redacted samples at nominal `t=0..9` seconds. Each proves whether
   `wlan0` exists and whether its exact driver remains, and records normalized
   carrier/operstate when readable. This is ten samples over a nominal
   nine-second span, not a measured ten-second lower bound. No network-send
   command is dispatched; background radio traffic is unmeasured. Every sample
   also revalidates the unchanged `SIGCHLD` disposition and unreaped child.
9. **Post-sample cleanup proof.** Repeat the complete subtree, PID-namespace,
   global-accounting, persistent-object, and PID 1 FD/credential/root/cwd/
   namespace scans after the last sample. Then reap only the exact
   direct child with `waitpid`, validate its recorded status, and immediately
   repeat global and parent-state accounting so PID reuse, respawn, or
   capability transfer is not hidden. Close the held namespace FD and require
   the exact original PID 1 baseline. No helper or external diagnostic service
   is permitted to restart it. Any difference is `NO_PROOF`.
10. **Terminal publication.** Publish one exact-envelope terminal receipt using
   temporary-file fsync, atomic no-replace publication, and directory fsync.
   It binds every phase, signal attempt/accept count, both cleanup proofs,
   child exit/reap status, sample set, failure stage/rc/errno, and prior intent
   hash. An existing, torn, linked, symlinked, wrong-mode, or extra state member
   fails closed.

This design does not claim `pidfd_send_signal`; phase-owned pidfds serve only
the seccomp broker and never select the effect target. Signal identity depends on the
qualified direct-child/no-alternate-wait structure: an exited but unreaped
child retains its PID, so the final-check-to-signal race can yield only the
same child or its zombie, never a reused unrelated process. Any violation of
that structure is a build/self-check failure, not a runtime fallback.

## Terminal semantics

| Terminal | Required proof | What it does not prove |
|---|---|---|
| `TRANSFER_FEASIBLE` | exact helper tree gone, no transferred/persistent capability, exact PID 1 baseline restored, and `wlan0` plus its bound driver persist in all ten samples | Debian ownership, association, IP reachability, or zero packets |
| `TRANSFER_REFUTED` | the same exact cleanup and parent-state proof plus a proved missing interface or changed/absent driver in the bounded samples | why the kernel state changed or which future supervisor design is safe |
| `NO_PROOF` | any incomplete, inconsistent, unreadable, timed-out, uncertain, or drifted boundary | feasibility, refutation, current resident health, or retry authority |

All three terminals grant no candidate authority. Once device intent may have
existed, the effect is never replayed. An exact pre-signal cancellation with
signal-attempt count zero is consumed and is not a Wi-Fi ownership decision.
`TRANSFER_FEASIBLE` and `TRANSFER_REFUTED` prove a decision only; they do not
select a live owner.

## Host transaction and bridge lease

The host runner must remain small and reachable-code based. It has separate
closures for reusable capability qualification and in-flight execution:

- the capability closure contains the native command/dispatcher/scanner,
  protocol parser, tests, this contract, and recovery assumptions;
- the runtime closure contains only code and immutable consumed bytes required
  to execute or reconcile the exact run; and
- prose, tests, or historical build-source drift cannot block observation-only
  reconciliation after durable host intent.

Before the effect, the host acquires one exclusive bridge-generation lease and
holds it through final target validation, durable host intent publication, the
single command send, and receipt framing. The lease binds the bridge process
PID/start time, exact serial endpoint realpath/device identity, and one
connection generation. A per-command lock followed by reconnect is
insufficient. Replacement, disconnect, ambiguity, or loss before the send
stops; loss after host intent enters observation-only reconciliation.

Host journal records use no-clobber temporary publication, file fsync, atomic
publication, and directory fsync. Exact file type, mode, link count, member
set, sequence, and hashes are validated. The journal distinguishes:

- prepared but no host intent: no effect, fresh approval required;
- durable host intent but no proven device intent: uncertain, never resend;
- device intent or signal-attempt proof: consumed, observation only;
- terminal receipt: host-only result publication; and
- missing/torn evidence: `NO_PROOF`, never inferred as no effect.

An empty transaction directory proves neither current health nor absence of a
device effect unless its creation boundary and the lack of host intent are
both exact. Current health always requires a fresh read-only status receipt.
After reconnect, status returns the bounded complete terminal or committed
stage receipts, not merely a hash, so host reconciliation can publish a result
without repeating the transaction.

If durable host intent exists but status proves, from the unchanged build,
boot generation, persistent state identity, and complete one-use acceptance
ledger, that the ledger remains pristine with count zero and no accepted nonce
of any value, the approval is consumed but the device effect count is exactly
zero. Merely proving that the bound nonce is absent is insufficient. Fresh
status may then close native health without recovery. A different nonce,
missing, reset, rolled-back, or ambiguous acceptance state remains `NO_PROOF`
and recovery-required; absence is never inferred from silence.

## Recovery boundary

Any signal attempt, an uncertain signal dispatch, or a device-side accepted
transaction whose complete zero-attempt cancellation cannot be reconstructed
leaves `HEALTH_PENDING_WIFI_RECOVERY` and moves the current boot to status-only
`RECOVERY_PARKED` as soon as the committed stage is known. The transaction
never restarts the helper, reboots, flashes, arms handoff, or mounts UFS. Only
an exact pre-signal
cancellation that proves signal-attempt count zero, the same still-live helper,
and fresh unchanged health may close `RESIDENT_HEALTHY` without reboot; that
consumed transaction still cannot be retried. A spontaneous helper exit or a
signal attempt with return failure remains health-pending.

Recovery is one separate fresh-approved action that reboots the exact installed
diagnostic resident without replaying the ownership transaction. After reboot,
the read-only status command must prove the exact build and new boot generation,
auto-handoff disabled, helper ready and healthy, exact `wlan0`/driver, no active
transaction, and native control health. Only then may the run close
`RESIDENT_HEALTHY`.

On every later boot, a signal-attempt boundary or a possibly consumed device
transaction whose exact zero-attempt cancellation is not durable, and which
lacks an exact durable recovery intent, also enters status-only
`RECOVERY_PARKED`. It does not launch the helper, clear evidence, arm handoff,
or continue the transaction. An exact terminal pre-signal cancellation or a
proof that the complete one-use acceptance ledger is pristine, count zero, and
contains no nonce of any value may boot the same healthy helper, but the
consumed approval remains non-retryable. The
separately approved recovery verb above creates the recovery intent. The
following boot consumes it before helper launch, archives but never rewrites
the ownership transaction, starts one new contained helper generation, and
exposes the read-only status proof above. Thus host loss or power loss cannot
silently restart the helper and erase the observation boundary.

If recovery or physical Download/TWRP availability is ambiguous, stop. No
later candidate or other A90 effect may proceed from health-pending state.

## Verification matrix before `PASS_GO`

The implementation review must include at least:

- an exact mixed closure over every reviewed file as
  `relative-path\0size\0sha256\0` and these three exact negative entries as
  `relative-path\0ABSENT\0`: the retired H24 W0 runner, its retired test, and
  the unallocated H26 manifest. A file, directory, symlink, or other object at
  any negative path invalidates the closure;
- full AArch64 compile/link of the selected native closure and deterministic
  boot-only artifact reproduction;
- macro/profile tests proving the diagnostic commands are absent from ordinary
  production profiles and automatic handoff is disabled in the diagnostic;
- diagnostic-dispatch tests proving none of the three verbs reaches
  shell-prompt or command-end reaping, general `cat`/`run` is absent in the
  profile, and
  ordinary resident profiles are unchanged;
- H24-to-diagnostic tests proving no shell command runs during host preparation
  and any required live predecessor command is exact, post-approval,
  pre-transfer F1 control rather than D0;
- exact receipt framing, duplicate/contradictory fact, unknown-key, truncation,
  symlink, hardlink, wrong-mode, extra-member, and torn-publication tests;
- process tests for fork, exec, reparent, setsid, setpgid, unshare, namespace
  retention, nested PID namespaces, pre-snapshot escape attempts, zombies,
  kernel threads, PID reuse, forbidden alternate wait paths, `SIGCHLD=SIG_IGN`,
  `SA_NOCLDWAIT`, blocked SIGCHLD, disposition drift, procfs read failure, scan
  instability, and capacity exhaustion;
- capability-transfer tests for inherited/received FDs, `SCM_RIGHTS`, binder,
  ptrace/process-vm, pidfd-getfd, proc-fd duplication, namespace handles,
  capability/credential drift, SysV/POSIX IPC, BPF/keyring objects, parent FD
  drift, and forbidden post-baseline user tasks; every case must fail closed;
- proc-isolation tests proving native PID 1 and the non-dumpable outside broker
  are absent from the sole fresh procfs and every inherited procfs/old-root
  path is detached; launcher becomes non-dumpable before filter, every vendor
  stub can set only dumpable=1, and every vendor access to launcher `mem/fd/fdinfo/ns/
  root/cwd/exe/map_files`, control-pipe injection, listener/pidfd duplication,
  `PR_SET_PTRACER`, credential/dumpability drift, and compat
  open/openat/openat2 path fails;
- private-binderfs tests proving only three private nodes, every service manager
  and client inside the descendant tree, no global binder-device or PID 1
  Binder FD, complete reference cleanup, mount destruction, and exact
  H24-equivalent `wlan0`/driver health without network sends;
- private-IPC tests proving the required `property_service` shim, every AF_UNIX
  peer/shared-memory user, and all IPC objects remain inside the descendant
  tree's fresh IPC/mount namespaces, cannot pass FDs to PID 1, and leave zero
  endpoint/object/mount after cleanup;
- AF_UNIX broker tests covering leading-NUL abstract names, truncated and
  oversized `sockaddr_un`, FD reuse, pathname replacement, `bind`, `connect`,
  family-only autobind, `setsockopt(SO_PASSCRED)` with every value, other
  address-creating socket options, `sendto`, `sendmsg`, `sendmmsg`, `recvmsg`,
  `recvmmsg`, AArch64/compat-AArch32 dispatch, unknown audit architecture,
  `io_uring`, ancillary data, notification cancellation, listener-copy loss,
  attempted `CONTINUE`, and broker self-notification; require the sole filtered vendor launcher,
  unfiltered broker, exact pre/final `/proc/net/unix` and FD-reference equality,
  and rejection of every unaccounted socket inode;
- crash-prefix tests before host intent, after host intent, before/after device
  intent, before/after signal, during cleanup, during sampling, and before/after
  terminal publication; none may resend the transaction;
- bridge replacement/disconnect/generation-race tests that prove one lease
  spans target validation and the single send;
- terminal tests that repeat complete survivor checks after the sample window,
  distinguish proved absence/change from observer error, reconstruct the full
  terminal/stage evidence after reconnect, and never infer a Debian owner;
- recovery tests proving a new boot generation and restored helper health
  without ownership-effect replay, including recovery-marker publication,
  lost response, reboot return/cancellation, and parked boot without a marker;
- acceptance-ledger tests proving any different accepted nonce, nonzero count,
  reset, rollback, duplicate, or contradiction rejects the host-send-not-
  accepted path; bound-nonce absence alone is never proof; and
- exact action counters: one A90 effect command at most, zero handoff/UFS/
  reboot/flash/network-send commands inside it, and zero S22+/S20+ contact.

Benchmark telemetry is test-only and never a safety predicate. Record boottime
to resident-ready, snapshot stabilization time, device-intent fsync time,
signal-to-cleanup time, observation duration, terminal fsync time, CPU time,
peak RSS, temperature, and available clock/power counters. Unsupported data is
`not_available`; it is never fabricated and does not block a correct safety
terminal.

## Size and production-removal discipline

This diagnostic is disposable qualification machinery. The implementation
review must report native and host nonblank line counts, reachable dependency
counts, artifact-size delta, resident-ready delta, and idle CPU/RSS delta.
Exceeding either 1,200 nonblank lines for the new native module or 900 nonblank
lines for the host runner triggers an explicit decomposition review; it is not
a reason to weaken validation.

No diagnostic command, process scanner, ownership journal, or benchmark loop is
carried into the final headless server candidate. The production successor
receives only the ownership decision and the smaller boundary it justifies.

## Authorized sequence

1. Freeze and independently review this H0 design boundary, then commit only
   the accepted A90 documentation scope.
2. Only on design acceptance, implement the diagnostic native and host closure
   without allocating live authority.
3. Obtain an independent capability `PASS_GO` over the exact implementation.
4. Allocate a fresh identity and deterministic boot-only artifacts; perform
   ordinary host validation.
5. Prepare the diagnostic install from the exact durable H24 terminal and
   passive target/recovery evidence. If implementation review proves a live
   H24 predecessor command unavoidable, run only the exact post-approval F1
   pre-transfer control; never call it D0.
6. Use a fresh attended F1 approval for one diagnostic install, then use its
   new dedicated status verb to prove exact resident health.
7. Use a separate fresh attended D1 approval for one atomic transaction.
8. Observe to one terminal without replay.
9. After any signal attempt, uncertain signal dispatch, or accepted transaction
   without a durable exact zero-attempt cancellation, use the separate
   fresh-approved recovery verb and prove `RESIDENT_HEALTHY`; for an exact
   signal-attempt-count-zero cancellation, require fresh status health without
   reboot.
10. Only then use a proved decision in a new H0 headless successor design.

Nothing in this sequence grants standing authority or permits an H24 shell W0
retry.
