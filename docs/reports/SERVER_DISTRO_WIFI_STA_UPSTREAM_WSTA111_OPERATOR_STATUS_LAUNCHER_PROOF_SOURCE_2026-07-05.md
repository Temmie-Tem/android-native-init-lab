# WSTA111 Operator Status Launcher Proof Source Pass

Date: 2026-07-05 02:44 KST

## Scope

WSTA111 folds the WSTA110 smoke service launcher live proof into the WSTA108
operator server status bundle. This is a host-only source/status unit. It did
not run a new live device action, build or flash a boot image, reboot native
init, associate Wi-Fi, run DHCP, open a public tunnel, run public smoke, mutate
packet filters, touch userdata, or switch root.

## Changes

- Extended `run_wsta108_operator_server_status.py` with optional
  `--wsta110-service-launcher-proof-json`.
- The new input must be a private JSON file and must carry
  `wsta110-service-launcher-chroot-live-pass`; non-pass proof JSON remains
  fail-closed. A pass decision with missing required runtime markers is also
  blocked as incomplete proof.
- Added a compact `hardening.launcher_proof` overlay with redacted proof fields:
  service `dpublic-smoke-httpd`, user/group `a90www`, UID/GID `3901/3901`,
  no-new-privs, zero effective capabilities, public default-off, fail-closed
  branches, cleanup, final selftest, and remaining launcher profiles.
- Refined WSTA90 blocking text when the smoke proof is present:
  - old broad user/group blockers become
    `remaining service users/groups not live-proven beyond dpublic-smoke-httpd`;
  - old broad launcher blockers become
    `remaining service launchers not live-proven beyond dpublic-smoke-httpd`.
- Updated WSTA108 tests for WSTA110 pass proof ingestion, non-pass proof blocking,
  template visibility, and redacted Markdown summary output.

## Existing Proof Consumed

Private input:

```text
workspace/private/runs/server-distro/wsta110-service-launcher-live-20260704T173234Z/wsta110_result.json
```

Status regeneration:

```text
workspace/private/runs/server-distro/wsta111-operator-status-launcher-proof-20260705T0241KST/wsta108_operator_server_status.json
```

Result:

- Decision: `wsta108-operator-server-status-source-pass`
- Server state: `SERVER_PROFILE_READY_DEFAULT_OFF`
- Public state: `PUBLIC_OFF`
- `service_launcher_proof_supplied=true`
- `service_launcher_smoke_live_proven=true`
- Launcher proof state: `SMOKE_SERVICE_LAUNCHER_LIVE_PROVEN`
- Remaining launcher profiles: `cloudflared-quick-tunnel`,
  `dropbear-admin-usb`, `dpublic-hud`, `wsta-native-uplink-helper`
- Remaining blocking items:
  - `remaining service users/groups not live-proven beyond dpublic-smoke-httpd`
  - `syscall traces not captured`
  - `packet-filter backend not inventoried`
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

- WSTA108 focused tests: `11 tests OK`
- Full server-distro WSTA regression: `368 tests OK`
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.

## Next

WSTA112 should either refresh the hardening status overlays from already-proven
packet-filter evidence or extend the WSTA110 proof shape to the next concrete
service profile. Do not mark all profiles proven until each has its own bounded
runtime proof.
