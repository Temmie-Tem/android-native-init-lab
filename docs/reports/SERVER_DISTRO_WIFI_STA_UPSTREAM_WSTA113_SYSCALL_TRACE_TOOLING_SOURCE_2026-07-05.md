# WSTA113 Syscall Trace Tooling Source Pass

Date: 2026-07-05 02:58 KST

## Scope

WSTA113 stages the source/rootfs precondition for syscall trace profile capture.
This is a host-only source unit. It did not run a live device action, build or
flash a boot image, reboot native init, associate Wi-Fi, run DHCP, open a public
tunnel, run public smoke, mutate packet filters, touch userdata, switch root, or
capture a live syscall trace.

## Changes

- Added opt-in syscall trace tooling support to
  `prepare_wsta3_sta_rootfs.py`.
  - `--stage-syscall-trace-tools` installs `strace` into the private Debian
    rootfs when it is not already present.
  - The default remains off; ordinary WSTA3 rootfs prep does not pull new
    packages or run trace tooling.
  - If `strace` is already present, the prep path restores usrmerge symlinks and
    records the tool as ready without package extraction.
- Added syscall trace metadata to the WSTA3 summary:
  - target profile: `dpublic-smoke-httpd`;
  - public default: `off`;
  - source readiness only when the tool is present and explicitly requested.
- Added `/etc/a90-server-distro-stage` markers for the next bounded trace unit:
  - `syscall-trace-tool=/usr/bin/strace`
  - `syscall-trace-target=dpublic-smoke-httpd`
  - `syscall-trace-profile-source=deferred-WSTA114`
  - `syscall-trace-public-default=off`

## Non-Claims

- WSTA113 does not prove a syscall profile.
- WSTA113 does not retire the operator-status blocker `syscall traces not
  captured`.
- WSTA113 does not make any public profile always-on ready.

The next proof unit must run the prepared tool against the bounded
`dpublic-smoke-httpd` service profile and preserve the trace artifact privately.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_prepare_wsta3_sta_rootfs

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  $(find workspace/public/src/scripts/server-distro -maxdepth 1 -type f \
    \( -name 'run_wsta*.py' -o -name 'prepare_wsta3_sta_rootfs.py' \) | sort -V)

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_prepare_wsta3_sta_rootfs \
  $(find tests -maxdepth 1 -type f -name 'test_server_distro_wsta*.py' \
    -printf '%f\n' | sort -V | sed 's/^/tests./; s/\.py$//' | tr '\n' ' ')
```

Result:

- Focused WSTA3 rootfs regression: `31 tests OK`.
- Full server-distro WSTA regression: `375 tests OK`.
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.

## Next

WSTA114 should use `--stage-syscall-trace-tools` on a private rootfs, run a
bounded `strace` capture for `a90-service-launch dpublic-smoke-httpd ...`, and
convert the captured syscall set into a private profile summary. Keep public
exposure off and do not claim Dropbear or other service profiles from the smoke
HTTPD trace.
