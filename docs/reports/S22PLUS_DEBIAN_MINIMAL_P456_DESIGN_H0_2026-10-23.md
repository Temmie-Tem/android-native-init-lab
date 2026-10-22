# P456: minimal Debian boot profile — H0 design

## Bounded task and completion criterion

Prepare one S22+ FYG8 automatic-boot candidate that runs a minimal Debian
initialization sequence followed by the existing packaged runlevel-2 services.
H0 completion requires an exact dependency declaration, checked real producers
and consumers, ARM64 component/integration qualification, identical actual A/B
packages, independent review and an unexecuted finite attended entry. No device
effect or approval is included in this work. A90 and S20+ are untouched.

This design precedes implementation. The retained architecture remains vendor
kernel -> Debian-owned initramfs PID1 -> protected installed-root admission ->
installed Debian SysVinit as host PID1. It introduces no second service manager.

## Current evidence and selected change

P455 recovered P452's exact early/runtime pair after P454's journal replay.
The pair proves installed Debian PID1 and rcS entry/fork on its first retained
boot, without rcS completion, services, SSH or shutdown proof. P454's complete
root comparison failed. Neither that failure nor missing later records locates
a stall. This candidate prioritizes the smallest functional boot over further
causal instrumentation.

Use the retained single-CPU/idle choice and a separately named twelve-row
historical selection: the prior ten exact rows plus P452's exact pair from
closed P455. Both complete current clean protected-root admissions remain
mandatory; history only identifies permitted files and cannot admit unexplained
entries. All consumed candidates and their original source provenance remain.

Replace only the full sixteen-script rcS dispatch with this fixed sequence:

1. Check the already supplied proc, sysfs, tmpfs `/dev` and `/run`, devpts,
   shared-memory tmpfs and `/run/config` configfs; check character devices
   required by the packaged workload and establish the existing RAM lock
   directory with its declared metadata. The fixed RAM random and urandom
   nodes are created if absent and checked as root-owned 0666 character devices
   1:8 and 1:9; no general device scan or block alias is added.
2. Run the installed Debian `hostname.sh` script.
3. Run the installed Debian `mdev` script.
4. Run the installed Debian `urandom` script.
5. Run the installed Debian `bootmisc.sh` script.

Keep the original eight runlevel-2 scripts, service programs, local service
proof, one NCM attempt, pinned same-boot SSH checks and fixed shutdown. The
existing witness supplies virtual mounts and device links before this sequence.
The archived `/etc/modules` has no active entries, fstab is empty, and fixed
module preparation already precedes admission. The USB service uses the moved
`/run/config` mount. No pstore/securityfs mount, generic networking, udev, module
loader or broad mount-all step is needed by the declared workload. Check these
dependencies against the sealed installed archive and integration result.

Packaged script exit status is only script status: in particular, `urandom`
can mask a seed-save error. Do not promote exit zero into entropy renewal,
mount, service, network or clean-shutdown proof.

## Required workload and optional observation

Stage the fixed minimal program as one additional sealed RAM asset using the
existing generic asset copier. Pin its bytes and metadata before the existing
rcS child fork. The child selects this program regardless of optional channel
availability. A failed required asset/dependency/script stops this workload;
an observation failure must never fall back to the full rcS sequence.

Reuse the bounded nonblocking script channel with a declaration for exactly
the selected steps. Keep packet completeness distinct from child status and
functional proof. Do not add proc sampling, tracefs, a daemon, a persistent
evidence file, a writable lifetime or an extended deadline. Legacy selections
retain their existing declarations and workload semantics.

## Authority and validation

Adopt the exact new selection in automatic-boot policy, its common-contract
incorporation and the S22+ target contract, with independent review of the
changed execution closure. The two admitted writable lifetimes, mutable-root
rules, 300000 ms device deadline, 360-second host observation, no-repair/no-replay
rules and physical original-A recovery are unchanged.

Validate positive minimal boot and the failures that matter: missing supplied
dependency, modified/missing required program, packaged-script nonzero status,
optional channel unavailable, exact-history rejection and both current-root
admissions. Exercise the original packaged services and pinned SSH semantics in
ARM64 qualification, then inspect actual packaged payloads and A/B identity.
Retain source snapshots and raw results privately. Qualification proves the
host/VM capability only; it cannot prove FYG8 service or USB behavior.

Only after H0 completion may an exact attended one-operation/3600-second
approval phrase be presented. The existing manual terminal entry is sufficient;
extending the ordinary-terminal bridge is outside this bounded change.
