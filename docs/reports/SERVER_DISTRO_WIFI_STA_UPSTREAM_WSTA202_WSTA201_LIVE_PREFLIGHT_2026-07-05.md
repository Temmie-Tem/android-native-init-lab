# WSTA202 WSTA201 Live Preflight

Date: 2026-07-05 17:53 KST

## Verdict

WSTA202 adds a host-only final preflight gate before any attended
WSTA200/WSTA198 live handoff.  It consumes the private WSTA201 status JSON,
validates the existing WSTA200 handoff wrapper and WSTA198 live wrapper paths,
re-runs WSTA201 from the current WSTA200 handoff, and compares a
token-independent stable status view.

Result: PASS.

Current preflight state:

```text
BLOCKED_OPERATOR_TOKEN_REQUIRED_DEFAULT_OFF
```

The WSTA200 handoff remains current and ready for an attended handoff, but
immediate live execution remains false because the private
`A90_PRIVATE_WSTA161_LOAD_TOKEN` environment variable was not present in this
host-only proof.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta202_wsta201_live_preflight.py`.
- Added focused tests in
  `tests/test_server_distro_wsta202_wsta201_live_preflight.py`.

## Proof

Run:

```text
workspace/private/runs/server-distro/wsta202-wsta201-live-preflight-20260705T175342KST/
```

Decision:

```text
wsta202-wsta201-live-preflight-pass
```

Input:

```text
workspace/private/runs/server-distro/wsta201-wsta200-handoff-status-20260705T175021KST/wsta201_wsta200_handoff_status.json
```

Generated private artifacts:

```text
workspace/private/runs/server-distro/wsta202-wsta201-live-preflight-20260705T175342KST/wsta202_result.json
workspace/private/runs/server-distro/wsta202-wsta201-live-preflight-20260705T175342KST/wsta202_wsta201_live_preflight.json
workspace/private/runs/server-distro/wsta202-wsta201-live-preflight-20260705T175342KST/wsta202_wsta201_live_preflight.md
workspace/private/runs/server-distro/wsta202-wsta201-live-preflight-20260705T175342KST/wsta201-recheck/wsta201_result.json
```

Key checks:

```text
status_valid=true
wsta201_recheck_valid=true
status_stable_view_match=true
live_preflight_valid=true
handoff_current=true
ready_for_attended_live_handoff=true
ready_for_immediate_live_execute=false
private_token_env_present=false
private_token_matches_wsta161=false
```

## Status Meaning

WSTA202 distinguishes three things:

- `status_stable_view_match=true` means the prior WSTA201 status still matches
  a fresh WSTA201 recheck, ignoring token-presence fields that may legitimately
  change between host sessions.
- `ready_for_attended_live_handoff=true` means the default-off WSTA200 handoff
  wrapper remains structurally current.
- `ready_for_immediate_live_execute=false` means this proof did not observe the
  private token in the host environment.

If the private token is deliberately supplied and WSTA202 is re-run, the
expected ready state is:

```text
READY_FOR_ATTENDED_WSTA200_WRAPPER_EXECUTION_DEFAULT_OFF
```

WSTA202 still does not execute the wrapper in that state.  It only reports that
the operator may manually run the existing private WSTA200 handoff wrapper after
final human confirmation.

## Safety Boundary

This proof did not flash, reboot, contact the device, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, switch root,
execute the WSTA200 handoff shell, run WSTA198 live, supply the WSTA161 token
to the device, run native health, load a seccomp filter, or enforce seccomp.

## Validation

- `py_compile`:
  - `run_wsta202_wsta201_live_preflight.py`
  - `test_server_distro_wsta202_wsta201_live_preflight.py`
- Focused WSTA202 tests: `6 tests OK`.
- WSTA202 proof run: pass.
- Full server-distro regression: `741 tests OK`.

## Next

Attended live remains default-off and blocked until the operator deliberately
supplies `A90_PRIVATE_WSTA161_LOAD_TOKEN` and re-runs WSTA202 to obtain
`READY_FOR_ATTENDED_WSTA200_WRAPPER_EXECUTION_DEFAULT_OFF`.  Only then should
the existing private WSTA200 handoff wrapper be run manually.
