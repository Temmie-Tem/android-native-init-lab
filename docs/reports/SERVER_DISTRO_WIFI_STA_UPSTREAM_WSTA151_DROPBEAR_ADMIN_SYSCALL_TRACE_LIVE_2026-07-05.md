# WSTA151 Dropbear Admin Syscall Trace Live Pass

Date: 2026-07-05 11:45 KST

## Scope

WSTA151 captures the remaining `dropbear-admin-usb` syscall profile before
broader containment or seccomp enforcement.  It reuses the WSTA119/WSTA120
bounded admin model: root-owned Dropbear bound only to the USB/NCM admin
address, an ephemeral private `a90admin` key for the run, `a90admin` login
proof, and root-login rejection.

This unit did not build or flash a boot image, reboot native init, associate
Wi-Fi, run DHCP, open a public tunnel, mutate packet filters, write userdata,
or switch root.  The only device-side mutation was the explicit live-gated
SD work-image chroot staging required to run Dropbear under `strace`, followed
by cleanup.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta151_dropbear_admin_syscall_trace.py`.
- Added focused tests in
  `tests/test_server_distro_wsta151_dropbear_admin_syscall_trace.py`.
- The runner:
  - uses the WSTA115 strace rootfs image by default;
  - requires explicit live/trace/key/root-negative-test/artifact/cleanup acks;
  - stages `a90admin` UID/GID `3903/3903` only inside the mounted SD work image;
  - starts `/usr/sbin/dropbear -F -E ... -s -w -j -k` under `strace`;
  - proves `a90admin` login and root SSH rejection;
  - snapshots the growing trace before fetching it, so the fetch SSH session
    does not trace its own `cat`;
  - saves raw trace, syscall list, and Dropbear log privately.

## Live Result

Run:

```text
workspace/private/runs/server-distro/wsta151-dropbear-admin-syscall-trace-live-20260705T113918KST/
```

Decision:

```text
wsta151-dropbear-admin-syscall-trace-live-pass
```

Resident:

```text
A90 Linux init 0.11.158 (v3402-dpublic-hud-presenter-restart-policy)
```

Input image:

```text
workspace/private/runs/server-distro/wsta115-strace-rootfs-20260705T0309KST/debian-bookworm-arm64-wsta115-strace.img
sha256=40a01268ae6f77d1548dd71f9ef30f4d31fdce437d90a6edcc7721f0e26dd159
```

Key proof:

- `a90admin` SSH passed with UID/GID `3903/3903`.
- root SSH was rejected.
- root `authorized_keys` was absent.
- Dropbear command included `-s -w -j -k`.
- Bind scope was the USB/NCM admin address only.
- Trace file and syscall profile were non-empty.
- Core daemon syscalls were observed: `execve`, `socket`, `bind`, `listen`.
- Connection handling was observed through `accept`.
- Dropbear log policy stayed clean: no `Password auth succeeded`.
- Trace artifacts were saved privately.
- Runtime cleanup removed the private admin key and trace directory.
- Chroot cleanup/postcheck passed.
- Final device health stayed clean: `selftest fail=0`.

Captured syscall-name profile count: `53`.

Captured syscall names:

```text
accept
bind
brk
chdir
clock_gettime
clone
close
connect
dup3
execve
execveat
exit_group
faccessat
fcntl
getcwd
getegid
geteuid
getgid
getpeername
getpid
getppid
getrandom
getsockname
getuid
listen
lseek
mmap
mprotect
munmap
newfstatat
openat
pipe2
prctl
prlimit64
pselect6
read
rseq
rt_sigaction
rt_sigreturn
set_robust_list
set_tid_address
setgid
setgroups
setresgid
setresuid
setsid
setsockopt
setuid
socket
statfs
wait4
write
writev
```

Artifact metadata:

- raw trace snapshot: private artifact saved, size `128661`, SHA256
  `57c6d2edc78c6565a792dac7d26c4db97e52a79f7527c13806b5b612ee897ab7`.
- syscall list: private artifact saved, size `436`, SHA256
  `fad7d643ced227b67b967f9545167f883ebeb7cbf3c4f13d8c03314041ec8eba`.
- Dropbear log snapshot: private artifact saved, size `556`, SHA256
  `436f132d9ea781be77c0badc392c1f5010fedf87f9fc9f3d94f2ad99c55577e1`.

Cleanup note:

- The trace-specific cleanup output reported `dropbear_absent=0` transiently,
  but `trace_cleanup_ok=true` because the private key and trace directory were
  removed, and the shared WSTA94 chroot cleanup/postcheck passed.
- The runner's final `selftest` reported `pass=12 warn=1 fail=0`.
- A post-run `netservice start` recovered the native transport to steady state:
  `tcpctl=ready`, `transport.upload=tcpctl-ready`, and
  `tcpctl_host.py status` returned `a90_tcpctl v1 ready`.

## Fixed During Run

Three bounded failed attempts were useful and did not regress device health:

- `20260705T1127KST`: snapshot parsing used `/usr/bin/awk` and
  `/usr/bin/sort`, which are not present in the native shell.  Fixed by using
  `/bin/busybox awk/sort/wc/grep/chmod/cat`.
- `20260705T113107KST`: log policy rejected any `root login` string, but the
  negative root-login proof naturally emits a root-login rejection log.  Fixed
  the policy to reject only `Password auth succeeded`.
- `20260705T113429KST`: fetching the live trace through the traced SSH daemon
  caused the trace to grow while `cat` was reading it.  Fixed by snapshotting
  trace/log files before fetching.

Each failed attempt completed cleanup and final selftest with `fail=0`.

## Interpretation

The last remaining pre-seccomp syscall profile in the WSTA150 operator status
is now live-captured for `dropbear-admin-usb`.  This does not enforce seccomp
yet; it provides the measured daemon baseline for a later policy derivation
unit.

The proof also preserves the existing security boundary: public exposure stayed
off, the daemon was USB/NCM-admin scoped, root login stayed disabled, password
auth did not succeed, and private key/trace artifacts stayed under
`workspace/private/`.

## Validation

Commands:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta151_dropbear_admin_syscall_trace.py \
  tests/test_server_distro_wsta151_dropbear_admin_syscall_trace.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  test_server_distro_wsta151_dropbear_admin_syscall_trace

PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest discover \
  -s tests -p 'test_server_distro*.py'
```

Results:

- Focused WSTA151 tests: `10 tests OK`.
- Full server-distro regression: `525 tests OK`.
- WSTA151 live: `wsta151-dropbear-admin-syscall-trace-live-pass`.
- Final device status: `tcpctl=ready`, `transport.upload=tcpctl-ready`.
- Final device selftest: `pass=12 warn=1 fail=0`.

## Next

Fold the WSTA151 Dropbear admin syscall profile proof into WSTA108 operator
status so `dropbear-admin-usb` is no longer listed as the remaining syscall
profile.  After that, derive concrete seccomp policy from the live baselines.
