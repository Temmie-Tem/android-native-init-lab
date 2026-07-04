# WSTA121 Operator Status Dropbear Admin Proof Source Pass

Date: 2026-07-05 04:52 KST

## Scope

WSTA121 folds the private WSTA120 Dropbear admin live proof into the existing
WSTA108/WSTA90 operator server status bundle. This is a host-only source/status
unit. It reads existing private proof JSON files and emits a redacted private
operator status artifact.

This unit did not run a device action, build or flash a boot image, reboot
native init, associate Wi-Fi, run DHCP, open a public tunnel, run public smoke,
mutate packet filters, touch userdata, or switch root.

## Changes

- Updated `run_wsta108_operator_server_status.py` to accept
  `--wsta120-dropbear-admin-proof-json`.
- Added a compact `dropbear_admin_proof` status section under
  `server_status.hardening`.
- The proof consumer requires the WSTA120 pass decision and fail-closes unless
  the proof includes all required runtime evidence:
  - explicit live gate;
  - baseline/final selftest fail-zero;
  - remote image ready;
  - chroot mount ready;
  - admin stage pass;
  - `a90admin` SSH pass with UID/GID `3903/3903`;
  - root SSH rejected;
  - admin key cleanup OK;
  - final chroot cleanup OK;
  - final Dropbear, mount, and loop absence.
- The WSTA90 blocker `dropbear admin user model not finalized` is retired only
  when the WSTA120 proof is complete.
- The generic launcher remaining-profile list now removes
  `dropbear-admin-usb` when the separate Dropbear root-boundary admin proof is
  live-proven. Syscall tracing remains separate, so `dropbear-admin-usb` still
  remains in the syscall-trace remainder.

## Source Proof

Private regenerated status:

```text
workspace/private/runs/server-distro/wsta121-operator-status-dropbear-admin-proof-v2-20260705T045218KST/wsta108_operator_server_status.json
```

Input proofs:

- WSTA88 workflow:
  `workspace/private/runs/server-distro/wsta107-status-hud-preflight-20260705T0200KST/wsta88_operator_workflow.json`
- WSTA90 manifest:
  `workspace/private/runs/server-distro/wsta108-server-status-hardening-input-20260705T0205KST/wsta90_service_hardening_manifest.json`
- WSTA94 packet filter:
  `workspace/private/runs/server-distro/wsta94-packet-filter-live-20260704T143227Z/wsta94_result.json`
- Packet-filter control summary:
  `workspace/private/runs/server-distro/packet-filter-control-ssh-live-20260704T160025Z/packet_filter_control_summary.json`
- WSTA110 service launcher:
  `workspace/private/runs/server-distro/wsta110-service-launcher-live-20260704T173234Z/wsta110_result.json`
- WSTA117/WSTA114 syscall trace:
  `workspace/private/runs/server-distro/wsta117-server-only-wsta114-live-v2-20260705T0407KST/wsta114_result.json`
- WSTA120 Dropbear admin:
  `workspace/private/runs/server-distro/wsta120-dropbear-admin-live-v6-20260705T044147KST/wsta120_result.json`

Result:

- Decision: `wsta108-operator-server-status-source-pass`
- Server state: `SERVER_PROFILE_READY_DEFAULT_OFF`
- Public state: `PUBLIC_OFF`
- Dropbear admin proof state: `DROPBEAR_ADMIN_LIVE_PROVEN`
- Dropbear admin user: `a90admin`
- Dropbear admin UID/GID: `3903/3903`
- Root SSH rejected: `true`
- Root authorized keys absent: `true`
- Password/root login and forwarding disabled: `true`
- Admin key cleanup OK: `true`
- Final Dropbear absent: `true`
- `dropbear admin user model not finalized` removed from
  `blocking_before_enforcement`
- Remaining blockers:
  - `remaining service users/groups not live-proven beyond dpublic-smoke-httpd/dropbear-admin-usb`
  - `remaining syscall traces not captured beyond dpublic-smoke-httpd`

The private status remained redacted: `public_url_value_logged=false` and
`secret_values_logged=0`.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta108_operator_server_status
```

Result:

- WSTA108 focused tests: `22 tests OK`
- Full server-distro WSTA regression: `384 tests OK`
- The WSTA94 runner-error JSON printed during the full run is the expected
  exception-path fixture from that unit test; unittest completed OK.
- `git diff --check`: OK

## Next

Dropbear admin model/runtime proof is now folded into operator status. The next
bounded unit should target a remaining hardening gap without reopening public
exposure by default. The highest-value next source unit is to extend the
server-status proof model toward the remaining service profiles, starting with
cloudflared or HUD syscall/launcher proof selection.
