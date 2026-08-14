# A90 isolated-Debian security derivation (H0)

Date: 2026-08-15  
Target: Samsung Galaxy A90 5G only  
Tier: H0 host-only analysis  
Authority: none; no device, USB, ADB, Odin, device-network, installation, or UFS contact

This is an extension of the prior derivation, not a new security structure.
`candidate_eligible` and `device_install_authorized` remain false. No ordinal,
identity, build string, artifact, qualification, approval, or command was
allocated.

The required read order was followed: `AGENTS.md`,
`docs/operations/targets/A90_TARGET_CONTRACT.md`, `GOAL_A90.md`, the prior
report, the current consumers, and the derivation tool. The A90 validation
discipline was applied by re-deriving the current tree state and reading the
manifest validator and source consumers rather than treating declarations as
proof.

## Evidence boundary

The new dynamic input is the operator-preserved private trace:

```text
workspace/private/outputs/a90-isolated-debian-trace-2026-08-15/README.txt
workspace/private/outputs/a90-isolated-debian-trace-2026-08-15/session_strace.txt
workspace/private/outputs/a90-isolated-debian-trace-2026-08-15/observed_syscall_names.txt
workspace/private/outputs/a90-isolated-debian-trace-2026-08-15/trace_session.sh
```

`session_strace.txt` has 1,799 lines and SHA256
`ac32def66189fe7b3f5033987b460dd9f08dfd444c6b266a9d3c5377005f4f13`.
The tooling now ingests that file directly, parses every syscall name through
the host's AArch64 kernel headers, records the trace hash and line count, and
performs the reconciliation deterministically. Ingestion itself performed no
execution or network operation.

## Static derivation and the corrected upper-bound result

The static pass still disassembles each exact private AArch64 binary with
`aarch64-linux-gnu-objdump`, inspects every `svc #0`, and walks at most twelve
preceding instructions, stopping at branches and register-sourced
`mov x8/w8`. It also records caller-side immediates that enter the generic
`__syscall_cancel` wrapper. The reproduced counts are:

| binary | `svc` sites | resolved | unresolved | distinct resolved numbers |
|---|---:|---:|---:|---:|
| Dropbear | 194 | 185 | 9 | 83 |
| PID 1 | 149 | 145 | 4 | 63 |
| dispatcher | 127 | 123 | 4 | 47 |
| workload | 128 | 124 | 4 | 48 |
| raw union | — | — | — | 84 |

The raw resolved svc-site union remains:

```text
[17, 24, 25, 29, 35, 37, 46, 48, 49, 50, 53, 54, 56, 57, 59, 61, 62,
 63, 64, 66, 67, 78, 79, 80, 93, 94, 95, 96, 98, 99, 103, 113, 118, 119,
 120, 121, 123, 125, 126, 129, 131, 134, 135, 144, 146, 147, 149, 154,
 155, 157, 159, 160, 166, 167, 169, 172, 174, 175, 176, 177, 178, 179,
 198, 200, 201, 204, 205, 208, 209, 210, 214, 215, 216, 220, 221, 222,
 226, 233, 261, 278, 281, 293, 435, 436]
```

### Authoritative syscall-name mapping

`parse_syscall_header()` now reads both
`/usr/aarch64-linux-gnu/include/asm/unistd_64.h` and
`/usr/aarch64-linux-gnu/include/asm-generic/unistd.h`, resolving numeric
aliases instead of using an ad-hoc table. The relevant generic definitions
are visible at `asm-generic/unistd.h:87,170,192,210-213,386,530-533,570,
631,880-891`; the AArch64 header gives the same LP64 numbers at
`unistd_64.h:29,66,76,83-84,143,206-207,226,248`.

The five suspected spelling aliases were verified as follows:

| trace spelling | authoritative source relationship | number |
|---|---|---:|
| `fcntl` | `__NR_fcntl -> __NR3264_fcntl` | 25 |
| `fstat` | `__NR_fstat -> __NR3264_fstat` | 80 |
| `fstatat` / `newfstatat` | `__NR3264_fstatat` / `__NR_newfstatat` | 79 |
| `lseek` | `__NR_lseek -> __NR3264_lseek` | 62 |
| `mmap` | `__NR_mmap -> __NR3264_mmap` | 222 |

All 48 observed names map uniquely through this one source of truth. The
alias numbers were already in the raw static set; they are not additional
static gaps.

### The five static-analysis gaps

The trace-to-static reconciliation found exactly five observed numbers absent
from the raw 84-number svc-site union. Four are not genuine missing callers:
the bounded walk stops at the generic cancellation wrapper after the libc
caller has supplied the number in `x6`. `rt_sigreturn` is not a private ELF
svc site at all. No one of these five is classified as a genuine walk gap.

| syscall | number | root cause found by tooling | classification |
|---|---:|---|---|
| `pselect6` | 72 | `__select` loads `x6=72` at `0x64e94` and `0x64f00`, then calls `__syscall_cancel`; the generic path reaches `mov x8,x6` at `0x4fac4` | unresolved register-sourced site |
| `rt_sigreturn` | 139 | AArch64 signal-return trampoline supplied by the kernel/libc signal-delivery ABI, outside private ELF text | signal-trampoline entry |
| `accept` | 202 | `__libc_accept` loads `x6=202` at `0x674a8`, calls `__syscall_cancel` at `0x674c0`, and reaches the same generic register move | unresolved register-sourced site |
| `connect` | 203 | `__libc_connect` loads `x6=203` at `0x6754c`, calls `__syscall_cancel` at `0x67564`, and reaches the same generic register move | unresolved register-sourced site |
| `wait4` | 260 | `wait4` loads `x6=260` at `0xa1acc`, calls `__syscall_cancel` at `0xa1ae0`, and reaches the same generic register move | unresolved register-sourced site |

The relevant Dropbear unresolved generic sites are `0x4fac4`
(`__internal_syscall_cancel`, `mov x8,x6`) and `0x50da8`
(`__syscall_cancel_arch_start`, `mov x8,x1`). The separate `0x65164`
`syscall()` residual remains a runtime-number escape hatch, but it is not the
cause of these four observed numbers.

The static upper-bound claim **does not survive**. The corrected claim is:
the 84-number resolved svc-site union is a partial known set, not an upper
bound. The evidence-derived candidate numeric allowlist is the raw union plus
all mapped observed trace numbers, with register-sourced and signal-trampoline
gaps recorded. It contains 89 numbers. It is still only a candidate universe,
not a released seccomp syscall/argument policy.

## Dynamic trace and exercised scenarios

The preserved trace contains these 48 distinct names:

```text
accept, bind, brk, clock_gettime, clone, close, connect, dup3, execveat,
exit_group, fcntl, fstat, geteuid, getgid, getpeername, getpid, getrandom,
getsockname, gettimeofday, getuid, ioctl, listen, lseek, mmap, mprotect,
newfstatat, openat, pipe2, prlimit64, pselect6, read, readlinkat, rseq,
rt_sigaction, rt_sigprocmask, rt_sigreturn, set_robust_list, set_tid_address,
setresgid, setresuid, setsid, setsockopt, socket, uname, unlinkat, wait4,
write, writev
```

The mapped observed number set is:

```text
[24, 25, 29, 35, 56, 57, 59, 62, 63, 64, 66, 72, 78, 79, 80, 94, 96,
 99, 113, 134, 135, 139, 147, 149, 157, 160, 169, 172, 174, 175, 176,
 198, 200, 201, 202, 203, 204, 205, 208, 214, 220, 222, 226, 260, 261,
 278, 281, 293]
```

Evidence in the trace includes the listening socket and accepted connection
at `session_strace.txt:25,49-50`, `setresgid`/`setresuid` at
`:365-372` and `:404-411`, the Dropbear port-forwarding and PTY-disabled logs
at `:378-383`, public-key success at `:428-429`, the observed `execveat` path
at `:119`, and the parent reaping the SSH child with `wait4` at `:1785-1786`.
That `wait4` is Dropbear session-child reaping; it is not evidence of the
separate PID-1 lifecycle.

| scenario | actual result | evidence and remaining boundary |
|---|---|---|
| authenticated public-key session | exercised, PASS | operator README, lines 6-8; trace logs public-key success at `:428-429` |
| forced dispatcher with bounded request | exercised, PASS per operator harness | README line 7; `execveat` is present in the trace. The deliberate identity/path deviations below limit exact-root validity. |
| wrong client key | exercised, rejected | README line 8 records `Permission denied (publickey)`; no success is inferred from the valid-key session. |
| PTY request | exercised, refused | README line 9 records `PTY allocation request failed on channel 0`; server also logged PTY disabled. |
| connection dropped mid-handshake | exercised, sent | README line 10; the trace ends the failed connection with `Connection reset by peer` at `:1776-1780`. |
| port-forwarding refusal | not exercised in preserved trace | README line 12 records the old client-side malformed `-L` argument. The harness was fixed to use a valid nonzero local port, but this host returned socket `EPERM` before the retry could reach Dropbear. The server's generic “Port forwarding disabled” startup/session log is not counted as a forwarding-request refusal. |
| PID-1 fork/reap/shutdown | not exercised | README line 13; the separate bwrap/unshare attempt was denied by the host. The observed Dropbear `wait4` does not close this item. |
| workload steady state | not exercised | README line 13; exact private-root/identity namespace setup was unavailable. |
| malformed probe request | identity-gate only | no new closure; request parsing after exact identity remains a successor test. |

The `-L` invocation was corrected in
`workspace/private/outputs/a90-isolated-debian-trace-2026-08-15/trace_session.sh`
to use `127.0.0.1:${FORWARD_PORT}:127.0.0.1:22`, where `FORWARD_PORT` is
nonzero and configurable. A host-only retry reached the socket precondition,
then failed with `socket: Operation not permitted`; the added workload and
PID-1 attempts failed closed with bwrap's “No permissions to create a new
namespace” message. No device or device-network contact occurred.

### Deliberate deviations and validity

The trace README records all three deviations; they are not silently promoted
to exact-target evidence:

| deviation | effect on validity |
|---|---|
| borrowed invoking uid/gid | confirms the observed control path and `setresgid`/`setresuid` calls, but does not prove the distinct 3302-to-3301 transition or capability necessity |
| absolute service-home/probe paths | validates syscall names and broad Dropbear behavior, but does not bind path resolution to the final private root |
| passwd shell kept in agreement with `/etc/shells` | necessary to reach `authorized_keys`; it changes no syscall number, but is a harness prerequisite rather than independent rootfs proof |

## Corrected candidate and reconciliation

The manifest's corrected candidate allowlist is the following 89-number set:

```text
[17, 24, 25, 29, 35, 37, 46, 48, 49, 50, 53, 54, 56, 57, 59, 61, 62,
 63, 64, 66, 67, 72, 78, 79, 80, 93, 94, 95, 96, 98, 99, 103, 113, 118,
 119, 120, 121, 123, 125, 126, 129, 131, 134, 135, 139, 144, 146, 147,
 149, 154, 155, 157, 159, 160, 166, 167, 169, 172, 174, 175, 176, 177,
 178, 179, 198, 200, 201, 202, 203, 204, 205, 208, 209, 210, 214, 215,
 216, 220, 221, 222, 226, 233, 260, 261, 278, 281, 293, 435, 436]
```

The automated reconciliation reports `static_count=84`, `dynamic_count=48`,
`candidate_count=89`, `traced_outside_resolved_svc_union=[72,139,202,203,260]`,
and `traced_missing_from_candidate_allowlist=[]`. The regression test fails
if any syscall in the preserved trace is removed from the manifest-derived
candidate.

This remains deferred as a filter release. The raw generic cancellation and
setxid register sources, ioctl request arguments, all-ABI default-deny
behavior, clone3 denial, complete path coverage, and on-device negative tests
remain open.

## Capability minimum

Consumer/source review still gives these candidate minimums:

| component | candidate minimum | current evidence limit |
|---|---|---|
| PID 1 | empty | source uses identity check, signal setup, fork/wait/signal, and workload exec; exact PID-1 run remains unexercised |
| dispatcher | empty | source performs identity check, bounded readiness read, and bounded stdout; exact isolated execution remains unexercised |
| workload | empty | source performs service-owned readiness-file lifecycle and signal handling; steady state remains unexercised |
| key daemon | `CAP_SETGID`, `CAP_SETUID` | the trace now observes both `setresgid` and `setresuid`, but borrowed uid/gid calls retained uid/gid 1000, so exact 3302-to-3301 proof and necessity/absence negatives remain deferred |

The minimum pair is therefore narrowed by dynamic evidence but not closed.
All other capabilities remain absent in the candidate profile.

## `/proc` derivation

The trace observed these paths:

```text
/proc/interrupts
/proc/loadavg
/proc/net/dev
/proc/net/netstat
/proc/net/rt_cache
/proc/net/tcp
/proc/self/exe
/proc/sys/kernel/random/entropy_avail
/proc/vmstat
```

The first eight are observed global/non-scalar read paths; `/proc/self/exe`
is a per-task link. No finite global scalar value was derived, so the finite
scalar allowlist remains `[]`. Literal candidates still not observed are
`/proc/meminfo`, `/proc/stat`,
`/proc/sys/kernel/ngroups_max`, `/proc/sys/kernel/rtsig-max`, and
`/proc/sys/vm/overcommit_memory`. The observed path evidence narrows the item,
but PID-1/workload and exact namespace closure remain deferred.

## Deferred items and successor methods

- `seccomp-positive-syscall-argument-allowlist`: narrowed to the corrected
  89-number candidate; not closed. First successor is a socket-capable host
  rerun of the fixed valid-`-L` harness, followed by exact-identity private
  PID/user namespace tracing and then on-device negative tests.
- `capability-minimum-set`: narrowed to empty/empty/empty plus the observed
  key-daemon pair; not closed. Successor is an exact 3302-to-3301 run with
  capability-necessity and all-other-capabilities-negative tests.
- `proc-scalar-allowlist`: narrowed by the observed global paths but remains
  finite-scalar `[]`; not closed. Successor is exact PID-1/workload and
  remaining-path tracing with scalar/write negative tests.

No scenario was claimed closed without evidence. The unexercised scenarios
require a privileged isolated host/container that permits local sockets,
user/PID namespaces, the exact service identities, a private `/run`, and
guest exec support (or a full-system QEMU equivalent). After that host method,
the remaining exact-target negative testing is on-device and must remain a
separate authority gate.

## Verification

The final focused verification is recorded in the handoff:

```text
python3 -m py_compile workspace/public/src/scripts/server-distro/a90_isolated_debian_security_derivation.py  -> PASS
python3 -m unittest discover -s tests -p 'test_a90_isolated_debian_security_derivation.py'                  -> PASS
python3 -m unittest discover -s tests -p 'test_a90_isolated_debian_content_manifest.py'                      -> PASS
bash -n workspace/private/outputs/a90-isolated-debian-trace-2026-08-15/trace_session.sh                     -> PASS
```

The derivation CLI was also run with `--trace` against the preserved
`session_strace.txt` and returned exit code 0. The private derivation JSON,
raw trace, binaries, and key material remain under `workspace/private/`; no
private trace or key was staged. No S20+ or S22+ file was touched.
