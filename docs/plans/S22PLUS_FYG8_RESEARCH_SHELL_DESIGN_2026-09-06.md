# S22+ research shell: arbitrary syntax, bounded read-only view

Status: H0 design, NOT ACTIVE. Target SM-S906N/g0q/S906NKSS7FYG8.
The operator chose arbitrary shell syntax with a designed write barrier.
This is not the existing five-query P344 authority, and P344 remains consumed.

## Minimum useful scope

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

Current code has no immediate cancel: while a command runs, the device reads
the output pipe, not the TTY. Ctrl-C cannot be advertised as implemented.
Implementing immediate cancellation requires a narrow authenticated cancel
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

## Next implementation and qualification

Implement the fixed child isolation and test real ash pipelines/substitutions,
normal and nonzero exits, attempted file creation/truncation/rename, descriptor
escape, child group escape, output flood and timeout. Then implement and test
authenticated cancellation, including a subsequent successful command on the
same connection. Exercise the complete producer -> publisher -> lease -> close
summary path, not only a parser or synthetic result dictionary.

Only after that H0 unit and its changed-boundary review: build a fresh candidate,
register the exact new shell capability, perform normal D0/D1 as required and
obtain fresh attended F1 approval. The first F1 should be one bounded script of
successful read commands, one timeout/cancel and one subsequent command, followed
by mandatory rollback/health. No F1-ready or shell-activation claim exists yet.
