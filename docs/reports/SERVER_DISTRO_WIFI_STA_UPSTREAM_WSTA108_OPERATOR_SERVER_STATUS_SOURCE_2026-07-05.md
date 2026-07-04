# WSTA108 Operator Server Status Source Pass

Date: 2026-07-05 02:08 KST

## Scope

WSTA108 adds a host-only operator server status bundle for the WSTA public workflow.
It consumes existing redacted WSTA88 output and optionally WSTA90 service hardening
manifest output, then emits a compact JSON/Markdown status view. No device action,
native reboot, Wi-Fi connect, DHCP, public tunnel, public smoke, packet-filter
mutation, userdata action, switch-root, or boot flash ran.

## Changes

- Added `run_wsta108_operator_server_status.py`.
- Default execution is fail-closed unless `--emit-server-status` is supplied.
- Required input is a private WSTA88 workflow JSON whose decision is preflight or
  live pass.
- Optional input is a private WSTA90 service hardening manifest JSON.
- Output summarizes:
  - public exposure state and WSTA80/WSTA88 decisions;
  - native-owned Wi-Fi / Debian service-surface model;
  - WSTA88 lease, packet-filter, image-prep, and manual-stop state;
  - WSTA90 hardening state, service count, no-new-privs, capability-drop, seccomp,
    and blocking-before-enforcement items;
  - operator next actions that keep public exposure default-off.
- Updated `docs/operations/A90_WSTA_NATIVE_UPLINK_DPUBLIC_OPERATOR_RUNBOOK.md` with
  the WSTA88 preflight + WSTA108 server-status workflow.

## Live/Device State

No live device action was required for this source unit. The generated private
artifacts used existing local WSTA88/WSTA89 evidence only. Final read-only health
checks showed `selftest pass=12 warn=1 fail=0` and bridge
`connected-no-immediate-error`.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  $(find workspace/public/src/scripts/server-distro -maxdepth 1 -type f -name 'run_wsta*.py' | sort -V)

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  $(find tests -maxdepth 1 -type f -name 'test_server_distro_wsta*.py' \
    -printf '%f\n' | sort -V | sed 's/^/tests./; s/\.py$//' | tr '\n' ' ')
```

Result:

- `326 tests OK`
- The WSTA94 runner-error JSON printed during the run is the expected exception-path
  fixture from the unit test; unittest still completed OK.
- WSTA90 manifest generation from the existing WSTA89 audit passed.
- WSTA108 generation from the WSTA107 WSTA88 preflight artifact plus the WSTA90
  manifest passed with `SERVER_PROFILE_READY_DEFAULT_OFF`, `PUBLIC_OFF`, native-owned
  Wi-Fi, Debian service-surface consumer, packet filter ready, 5 hardening services,
  no-new-privs default true, capability drop required true, and seccomp profile source
  ready true.

## Next

The WSTA operator has a single default-off server status bundle now. Next useful
work is to turn the WSTA90 blocking items into one bounded implementation unit:
rootfs user/group staging plus a no-new-privs launcher plan, still without opening
public exposure by default.
