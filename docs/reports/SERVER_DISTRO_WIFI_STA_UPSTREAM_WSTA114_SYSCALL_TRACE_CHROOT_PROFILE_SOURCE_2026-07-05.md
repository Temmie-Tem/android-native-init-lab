# WSTA114 Syscall Trace Chroot Profile Source Pass

Date: 2026-07-05 03:07 KST

## Scope

WSTA114 adds the bounded live-gate runner for a private syscall trace profile of
the D-public smoke service. This is a source/harness unit. It did not run the
live trace, touch the device, build or flash a boot image, reboot native init,
associate Wi-Fi, run DHCP, open a public tunnel, mutate packet filters, touch
userdata, or switch root.

## Changes

- Added `run_wsta114_syscall_trace_chroot_profile.py`.
  - Default invocation is device-inert and fails closed until all explicit gates
    are supplied:
    - `--execute-syscall-trace-chroot-live`
    - `--allow-syscall-trace-live`
    - `--ack-private-trace-artifact`
  - Reuses the WSTA110 chroot/dropbear/service-hardening flow instead of adding
    another independent device path.
  - Builds and stages the existing D-public smoke helpers, then runs:
    `strace -f ... a90-service-launch dpublic-smoke-httpd a90-dpublic-smoke-httpd 127.0.0.1 8080`.
  - Drives one loopback HTTP GET and requires `A90_DPUBLIC_SMOKE_OK`.
  - Requires public exposure default-off before tracing.
  - Requires `NoNewPrivs=1`, zero effective capabilities, non-empty raw trace,
    non-empty syscall-name profile, and core smoke-server syscall evidence:
    `execve`, `socket`, `bind`, and `listen`.
  - Saves the raw trace and syscall list as private run artifacts only.
- Added `tests/test_server_distro_wsta114_syscall_trace_chroot_profile.py`.
  - Covers explicit gate behavior, default inert mode, marker staging, trace
    script structure, parser/profile behavior, artifact saving, classification,
    and safety boundaries.

## Non-Claims

- WSTA114 source pass does not prove that `strace` is present in the current live
  SD image.
- WSTA114 source pass does not capture or validate a live syscall profile.
- WSTA114 source pass does not retire `syscall traces not captured` from the
  operator status.
- The profile scope is smoke-service-only and must not be generalized to
  Dropbear, tunnel, HUD, or native-boundary services.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta114_syscall_trace_chroot_profile.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta114_syscall_trace_chroot_profile

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  $(find workspace/public/src/scripts/server-distro -maxdepth 1 -type f \
    \( -name 'run_wsta*.py' -o -name 'prepare_wsta3_sta_rootfs.py' \) | sort -V)

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_prepare_wsta3_sta_rootfs \
  $(find tests -maxdepth 1 -type f -name 'test_server_distro_wsta*.py' \
    -printf '%f\n' | sort -V | sed 's/^/tests./; s/\.py$//' | tr '\n' ' ')
```

Result:

- Focused WSTA114 runner tests: `9 tests OK`.
- Full server-distro WSTA regression: `384 tests OK`.
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.

## Next

Run the WSTA114 live gate only after confirming the SD work image contains
`strace` or has been rebuilt via WSTA113 `--stage-syscall-trace-tools`. The live
run should preserve private `wsta114_smoke.strace` and
`wsta114_smoke.syscalls` artifacts, then a later host-only status unit can fold
the proof into WSTA108 without broadening the profile beyond
`dpublic-smoke-httpd`.
