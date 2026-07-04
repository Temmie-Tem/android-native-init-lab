# WSTA118 Operator Status Syscall-Trace Proof Source Pass

Date: 2026-07-05 04:15 KST

## Scope

WSTA118 folds the WSTA117/WSTA114 private smoke-service syscall trace pass into
the WSTA108 operator server status bundle. This is a host-only source/status
unit. It did not run a new live device action, build or flash a boot image,
reboot native init, associate Wi-Fi, run DHCP, open a public tunnel, run public
smoke, mutate packet filters, touch userdata, or switch root.

## Changes

- Extended `run_wsta108_operator_server_status.py` with optional:
  - `--wsta114-syscall-trace-proof-json`
- The WSTA114 proof input must be private and must carry
  `wsta114-syscall-trace-smoke-chroot-live-pass`; non-pass proof JSON remains
  fail-closed.
- A pass decision with missing live trace evidence is blocked as incomplete
  proof.
- Added `hardening.syscall_trace_proof`, including:
  - service `dpublic-smoke-httpd`;
  - scope `smoke-service-only`;
  - server-only command shape;
  - public default-off and loopback GET proof;
  - no-new-privs and zero effective capabilities;
  - core syscalls `execve/socket/bind/listen`;
  - syscall-name profile and artifact-saved marker.
- When the proof is supplied and complete, WSTA108 retires only the broad
  WSTA90 blocker `syscall traces not captured`, replacing it with
  `remaining syscall traces not captured beyond dpublic-smoke-httpd`.

## Existing Proofs Consumed

Private inputs:

```text
workspace/private/runs/server-distro/wsta107-status-hud-preflight-20260705T0200KST/wsta88_operator_workflow.json
workspace/private/runs/server-distro/wsta108-server-status-hardening-input-20260705T0205KST/wsta90_service_hardening_manifest.json
workspace/private/runs/server-distro/wsta94-packet-filter-live-20260704T143227Z/wsta94_result.json
workspace/private/runs/server-distro/packet-filter-control-ssh-live-20260704T160025Z/packet_filter_control_summary.json
workspace/private/runs/server-distro/wsta110-service-launcher-live-20260704T173234Z/wsta110_result.json
workspace/private/runs/server-distro/wsta117-server-only-wsta114-live-v2-20260705T0407KST/wsta114_result.json
```

Status regeneration:

```text
workspace/private/runs/server-distro/wsta118-operator-status-syscall-trace-proof-20260705T0410KST/wsta108_operator_server_status.json
```

Result:

- Decision: `wsta108-operator-server-status-source-pass`
- Server state: `SERVER_PROFILE_READY_DEFAULT_OFF`
- Public state: `PUBLIC_OFF`
- `syscall_trace_proof_supplied=true`
- `smoke_syscall_trace_live_proven=true`
- Syscall-trace proof state: `SMOKE_SERVICE_SYSCALL_TRACE_LIVE_PROVEN`
- Syscall count: `18`
- Core syscalls observed: `execve`, `socket`, `bind`, `listen`
- Remaining blocking items:
  - `remaining service users/groups not live-proven beyond dpublic-smoke-httpd`
  - `remaining syscall traces not captured beyond dpublic-smoke-httpd`
  - `dropbear admin user model not finalized`

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta108_operator_server_status
```

Result:

- WSTA108 focused tests: `18 tests OK`
- Full server-distro WSTA regression: `396 tests OK`
- `git diff --check`: OK
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.

## Next

The smoke-service syscall trace blocker is retired only for
`dpublic-smoke-httpd`. The remaining hardening frontier is to extend the same
proof shape to the other service profiles, especially the Dropbear admin user
model before any always-on profile.
