# WSTA112 Operator Status Packet-Filter Proof Source Pass

Date: 2026-07-05 02:52 KST

## Scope

WSTA112 folds existing packet-filter live proof evidence into the WSTA108
operator server status bundle. This is a host-only source/status unit. It did
not run a new live device action, build or flash a boot image, reboot native
init, associate Wi-Fi, run DHCP, open a public tunnel, run public smoke, mutate
packet filters, touch userdata, or switch root.

## Changes

- Extended `run_wsta108_operator_server_status.py` with optional:
  - `--wsta94-packet-filter-proof-json`
  - `--packet-filter-control-summary-json`
- The WSTA94 proof input must be private and must carry
  `wsta94-packet-filter-loopback-live-pass`; non-pass proof JSON remains
  fail-closed.
- A pass decision with missing packet-filter runtime markers is blocked as
  incomplete proof.
- The control summary is optional, but if supplied it must prove helper
  preflight, default-drop apply, post-apply control-session continuity, restore,
  and cleanup.
- Added `hardening.packet_filter_proof`, including:
  - backend `legacy-iptables`;
  - policy `loopback-default-drop`;
  - loopback before/after proof;
  - default-drop observation;
  - exact restore;
  - final selftest fail-zero;
  - optional control-plane proof with helper version.
- When packet-filter proof is present, WSTA108 retires the stale WSTA90 blocker
  `packet-filter backend not inventoried`.

## Existing Proofs Consumed

Private inputs:

```text
workspace/private/runs/server-distro/wsta94-packet-filter-live-20260704T143227Z/wsta94_result.json
workspace/private/runs/server-distro/packet-filter-control-ssh-live-20260704T160025Z/packet_filter_control_summary.json
workspace/private/runs/server-distro/wsta110-service-launcher-live-20260704T173234Z/wsta110_result.json
```

Status regeneration:

```text
workspace/private/runs/server-distro/wsta112-operator-status-packet-filter-proof-20260705T0255KST/wsta108_operator_server_status.json
```

Result:

- Decision: `wsta108-operator-server-status-source-pass`
- Server state: `SERVER_PROFILE_READY_DEFAULT_OFF`
- Public state: `PUBLIC_OFF`
- `packet_filter_proof_supplied=true`
- `packet_filter_loopback_live_proven=true`
- `packet_filter_control_summary_supplied=true`
- `packet_filter_control_plane_live_proven=true`
- Packet-filter proof state:
  `PACKET_FILTER_LOOPBACK_AND_CONTROL_PLANE_LIVE_PROVEN`
- Launcher proof state: `SMOKE_SERVICE_LAUNCHER_LIVE_PROVEN`
- Remaining blocking items:
  - `remaining service users/groups not live-proven beyond dpublic-smoke-httpd`
  - `syscall traces not captured`
  - `dropbear admin user model not finalized`

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta108_operator_server_status

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  $(find workspace/public/src/scripts/server-distro -maxdepth 1 -type f \
    \( -name 'run_wsta*.py' -o -name 'prepare_wsta3_sta_rootfs.py' \) | sort -V)

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_prepare_wsta3_sta_rootfs \
  $(find tests -maxdepth 1 -type f -name 'test_server_distro_wsta*.py' \
    -printf '%f\n' | sort -V | sed 's/^/tests./; s/\.py$//' | tr '\n' ' ')
```

Result:

- WSTA108 focused tests: `15 tests OK`
- Full server-distro WSTA regression: `372 tests OK`
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.

## Next

The stale packet-filter backend blocker is now retired from the operator status
when proof is supplied. Remaining meaningful hardening work is syscall tracing
and per-service runtime proofs beyond `dpublic-smoke-httpd`, especially the
Dropbear admin user model before any always-on profile.
