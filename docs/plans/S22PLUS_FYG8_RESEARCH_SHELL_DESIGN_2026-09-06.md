# S22+ research shell: arbitrary syntax, bounded read-only view

Status: reviewed H0 implementation and ready2 published; fresh D0 passed after one authorized baseline reboot, F1 code issued but not returned/executed. Target SM-S906N/g0q/S906NKSS7FYG8.
The operator chose arbitrary shell syntax with a designed write barrier.
This is not the existing five-query P344 authority, and P344 remains consumed.

## Minimum useful scope

### Proportional scope decision

The first useful capability is arbitrary ash syntax over the existing USB
connection, reading the fixed child view and returning a bounded result. The
five-step first-F1 qualification is a test of that capability, not a general
container service or an unattended research session.

- Essential for this capability: the write barrier and descriptor/privilege
  isolation; bounded child/group cleanup and output; exact target/artifact
  binding; retained failure evidence; no uncertain replay; exact rollback and
  final health.
- Useful and already implemented: authenticated cancellation and a following
  command on the same descriptor. They are tested as selected P345 features,
  not introduced as prerequisites for every unrelated F1 experiment.
- Deferred: PTY/job control, persistent shell state, a new daemon, full procfs,
  networking, persistent writes, reboot/Download shell commands, long soak
  campaigns and another kernel build merely to repeat unchanged evidence.

The host's fixed five-session loop and the device's ability to accept a later
authenticated request are distinct. Independent re-review concluded
PASS_GO_P345_H0 under the host-bounded interpretation: the qualified host has
no sixth sender, later CLI, lease or reconnect path and proceeds to rollback.
The earlier NO_GO based solely on the inherited listener was withdrawn; no
runtime alteration or replacement AP was required. The device listener remains
available while awaiting physical rollback, but that grants no additional live
command authority. No device-side hard counter or listener termination is
claimed. Ready publication, fresh preparation and returned attended F1 approval
remain required; the review itself is not device authority.

Keep BusyBox ash, the authenticated framing and one host TTY connection.
Support shell pipelines, substitutions, variables and command arguments inside
a restricted read-only filesystem view. This means free shell syntax, not
unrestricted root access to the phone. No PTY job control, persistent cwd/state
across ash invocations, network, installation, reboot or Download command in
the first implementation. Parent PID1/transport/recovery remains outside the
child restriction and under the existing F1 owner.

Do not use a shell-text blacklist as the write barrier. `>` is only one route
to mutation: applets, inherited descriptors, ioctl, mounts and child processes
must also be considered. Nor should this grow into a general container manager.
One fixed child setup and the existing supervisor are sufficient design scope.

## Child boundary to implement and verify

1. Construct a private mount namespace and fixed small root view in volatile
   RAM. Make mount propagation private. Bind only the static BusyBox executable
   and reviewed read-only observation files; remount that view read-only before
   exec. No block nodes, gadget/control descriptors, debugfs, kernel memory,
   storage mounts, ADB sockets or host-control interface enter the view.
2. Do not expose all of procfs or sysfs. In particular, `/proc/*/root`, `fd`,
   `mem` and `kcore` can escape the intended observation surface or expose raw
   memory. Begin with a finite useful text view (kernel/memory/mount/uptime and
   selected process metadata plus UDC state). A full live `/proc` tree is not
   implied. Any refreshed snapshot is a parent-owned RAM artifact, not a device
   storage write. Exact files and setup bytes need review before implementation
   is activated.
3. Give the shell only stdin from a read-only null source and stdout/stderr
   pipes. Close every other inherited descriptor. Establish its process group
   first, then drop groups/UID/capabilities and apply no_new_privs so a later
   exec cannot regain privileges. Verify actual kernel/config support; this
   document is not proof that those steps already work on the candidate.
4. Install an inherited syscall filter before ash exec. Use a small tested
   syscall allowlist, not deny-by-name shell parsing. Writable/creating/truncating
   open modes, openat2/other unqualified open paths, filesystem mutation,
   ioctl/device control, network, ptrace/process-memory access, io_uring, mount,
   namespace creation/entry and privilege restoration are outside this first
   capability. Allow writes only through the inherited output pipes; prevent
   the child from obtaining another writable descriptor. Deny setsid/setpgid
   after setup so descendants cannot escape existing process-group cleanup.
   Unsupported syscalls fail the command, not silently widen the filter.
5. Bound CPU, address space, child count and output using the existing command
   deadline/output limits plus minimal per-child resource limits. Determine
   values with actual BusyBox tests; do not silently inherit an unbounded root
   process budget. Child setup failure must prevent ash execution.

These are requirements, not an implemented sandbox or a security claim. The
threat model remains accidental destructive commands and runaway local shell
jobs, not a claim of resistance to kernel exploitation or hostile same-UID
host replacement. Permanent boot-only and forbidden-memory/storage boundaries
remain unchanged.

## Continuous command and cancellation semantics

Reuse one TTY descriptor with successive existing logical authenticated
sessions, preserving current-boot and distinct nonce checks. Each submitted
command gets durable intent, raw RX/TX, one terminal result and no replay.
A normal nonzero exit, timeout or output truncation is a command outcome only
when its terminal frame and cleanup are proved; it must not be mislabeled
transport failure or generic success. The next command is allowed only under
that explicitly implemented successor contract. Malformed frames, missing
terminal, failed cleanup or connection loss still end the session and route to
the already bound rollback.

The consumed P344 code has no immediate cancel: while a command runs, the
device reads the output pipe, not the TTY. The H0 P345 successor implements a narrow authenticated cancel
message bound to the active command sequence, multiplexed with output reads.
It must kill/reap the owned group, preserve partial output and publish a
cancelled terminal before the next command. Partial/mismatched cancellation
never causes a resynchronization scan or command replay. Do not drop host
transport or send an unauthenticated signal byte as a fake cancel mechanism.

## First completed H0 implementation

`workspace/public/src/scripts/revalidation/s22plus_fyg8_research_shell_child.py`
is an unintegrated successor source transform. It preserves existing P344
bytes and adds two missing bounds: reaped-child output drain checks the
original command deadline, and the group-reap loop checks its existing deadline
before another successful wait iteration. A deadline-limited drain marks
TRUNCATED and then enters existing group cleanup. Cleanup uncertainty remains
an error; no new command or continuation permission is added.

The test compiles actual inherited exec/cleanup C functions with controlled
syscall fixtures. The predecessor reproduces an unbounded positive-output
loop; the repair passes normal, timeout, continuous-descendant-output and
continuous-reap cases. Native -Werror and AArch64 object compilation pass.
Independent verdict: PASS_GO_RESEARCH_SHELL_CHILD_DRAIN_H0.
This verifies control-flow bounds, not a real device sandbox or cleanup of
descendants allowed to escape the process group.

## P345 implementation and first qualification

The child boundary and authenticated host/device exchange now exist as H0
successor code. The private child view contains only BusyBox and snapshots of
meminfo, cpuinfo, uptime, version, mounts and the exact UDC state; it does not
provide a live process tree. Shell syntax is arbitrary inside this finite view,
not unrestricted root control. Child setup errors retain a bounded stderr
errno marker before exit 126; no setup failure falls through to ash.

The actual C frame parser, HMAC composition, command supervisor and cleanup
have been joined to the Python host using a local socket and real child
processes. Normal output, nonzero exit, authenticated cancellation, the actual
15-second timeout and a later successful command pass on one descriptor.
That test substitutes only platform wrappers, fixed parent witnesses and child
isolation; it is not proof of device mount/chroot or filtered BusyBox behavior.
Separate child tests/review must establish their own coverage accurately.

A host check found and repaired a cancellation-state collision: no request and
ACK0 had both used zero, so a normal command could falsely mark its cancel ACK
as already sent. No-request status is now 255; actual console regression covers
normal sequence-4 EXIT followed by late CANCEL, ACK1 and sequence 5. An active
cancel produces EXIT plus ACK0. Partial or invalid requests still stop without
resynchronization, and existing deadline/cleanup limits remain in force.

The first P345 F1 is deliberately a bounded qualification, not a later-action
lease. Five same-descriptor sessions each retain fixed parent id and run nonce
witnesses around the following sequence-4 command:

1. Read-only child canary: non-root identity, readable uptime, rejected file
   creation, absent probe file and exact success marker.
2. Expected exit 7, recorded as a command outcome rather than transport loss.
3. A command exceeding the unchanged 15-second deadline; proved cleanup.
4. Authenticated cancellation after command start; cancelled EXIT and ACK0.
5. Successful pipeline/substitution after the cancellation on the same FD.

The outer observation stays bounded at 300 seconds. No 120-second idle or
physical reopen is repeated here: P344 already proved the unchanged transport's
idle path, while this candidate tests the changed shell boundary and command
outcomes. Any missing terminal/cleanup, authentication failure or ambiguous
transport stops qualification and selects ordinary mandatory rollback. Even
complete qualification closes through exact rollback and healthy Android;
it opens no resident lease, generic live CLI or standing shell authority.

## Remaining device qualification

The changed execution closure passed independent H0 review, actual local
producer/consumer tests, immutable raw-receipt reopening and terminal projection.
Ready2 uses the unchanged AP `28631081B/7ee59a13`; the host-only successor fixed
an analysis-module import path found by the clean live CLI before device contact.
No replacement runtime or AP was necessary for that repair.

Fresh D0 passed after the operator-authorized one normal reboot cleared the
retained P344 baseline. That reboot is consumed; the new attended F1 code has
been issued but not returned or executed. The
first device test must establish the real mount/chroot read-only child boundary
and its five expected command outcomes, then exact rollback and final health.
Host tests do not establish those device facts. There is no lease step in this
qualification; general later research commands remain deferred.
