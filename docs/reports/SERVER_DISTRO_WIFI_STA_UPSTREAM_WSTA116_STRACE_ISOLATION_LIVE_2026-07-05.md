# WSTA116 Strace Isolation Live

Date: 2026-07-05 03:55 KST

## Scope

WSTA116 adds and runs a bounded diagnostic ladder for the WSTA114 syscall trace
timeout. It uses the same strace-enabled private SD work image and the same
chroot/Dropbear/service-hardening setup path as WSTA114, but splits the trace
into smaller probes. It did not flash a boot image, reboot native init,
associate Wi-Fi, run DHCP, open a public tunnel, run a public smoke request,
mutate packet filters, touch userdata, or switch root.

## Source Changes

- Added `run_wsta116_strace_isolation_ladder.py`.
  - Default invocation is device-inert.
  - Live execution requires:
    - `--execute-strace-isolation-live`
    - `--allow-strace-isolation-live`
    - `--ack-private-trace-artifact`
  - Reuses WSTA114/WSTA110/WSTA94 setup helpers instead of adding an independent
    device path.
  - Captures private diagnostic traces only under the run directory.
- Hardened WSTA114/WSTA116 smoke-child logging:
  - precreates the smoke server log with write permissions for the dropped
    `a90www` child.
  - defers nested `/proc` unmount and smoke cleanup to the native-side cleanup
    path to avoid SSH-probe cleanup hangs after traced children.
- Added `tests/test_server_distro_wsta116_strace_isolation_ladder.py`.

## Live Result

Run:

```text
workspace/private/runs/server-distro/wsta116-strace-isolation-live-v4-20260705T0354KST/
```

Decision:

```text
wsta116-blocked-smoke-background-strace
```

The live ladder removed the previous opaque timeout and isolated the failure:

- `strace /bin/true`: pass.
  - return code zero.
  - trace non-empty.
  - `execve` observed.
  - syscall count: `15`.
- `strace a90-service-launch dpublic-smoke-httpd /bin/true`: pass.
  - return code zero.
  - launcher exec decision logged.
  - trace non-empty.
  - `execve` observed.
  - syscall count: `39`.
- background `strace -f` around the full smoke orchestration: blocked.
  - trace spawned.
  - service launcher exec decision logged.
  - smoke child started as no-new-privs with zero effective capabilities.
  - trace non-empty.
  - core smoke server syscalls `execve`, `socket`, `bind`, and `listen` were
    observed.
  - loopback HTTP GET did not complete while the full orchestration was under
    `strace -f`.
  - syscall count: `59`.

All required private diagnostic artifacts were saved. Cleanup postcheck was
clean and final selftest stayed `fail=0`.

## Interpretation

WSTA114's blocker is no longer "strace missing" or "launcher cannot be traced".
The live evidence shows:

- ptrace/strace works in the chroot.
- `a90-service-launch` works under strace.
- the smoke server reaches bind/listen under strace.
- the over-broad trace shape that wraps the orchestration shell and HTTP client
  is the bad shape.

The next profile-capture attempt should trace only the smoke server process
under the launcher, while keeping the HTTP client outside the traced process
tree.

## Non-Claims

- This is not a WSTA114 profile pass.
- The `syscall traces not captured` blocker is not retired yet.
- WSTA108/WSTA90 must not consume WSTA116 as a hardening pass proof.
- The private raw traces and syscall lists are not committed.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta114_syscall_trace_chroot_profile.py \
  workspace/public/src/scripts/server-distro/run_wsta116_strace_isolation_ladder.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta114_syscall_trace_chroot_profile \
  tests.test_server_distro_wsta116_strace_isolation_ladder
```

Result:

- Focused WSTA114/WSTA116 tests: `18 tests OK`.
- WSTA116 live ladder: `wsta116-blocked-smoke-background-strace`.
- Final device selftest: `fail=0`.

## Next

WSTA117 should run a server-only trace shape:

```text
a90-service-launch dpublic-smoke-httpd strace -f -o <trace> a90-dpublic-smoke-httpd 127.0.0.1 8080
```

The loopback HTTP client should run outside that traced process tree. If that
passes, fold the same shape back into WSTA114 as the actual smoke-service
syscall profile capture.
