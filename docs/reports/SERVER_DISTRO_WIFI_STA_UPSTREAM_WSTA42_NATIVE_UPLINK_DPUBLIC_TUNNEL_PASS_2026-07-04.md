# WSTA42 Native-Owned STA Uplink + D-public Tunnel Live Pass

Date: 2026-07-04 KST

## Verdict

PASS.  D-public quick Tunnel publication now works over the native-owned STA
uplink path on resident V3394, with Debian used only as the chroot service
surface and native init retaining Wi-Fi ownership.

No boot flash, switch-root, userdata formatter action, forbidden partition write,
raw credential logging, confirm-token logging, DNS-value logging, or committed
public URL occurred in WSTA42.  The public URL was written only to the private
run directory and redacted from public outputs.

## Source Changes

- Added `workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py`.
- Added focused tests in `tests/test_server_distro_wsta42_native_uplink_dpublic_tunnel.py`.
- Required explicit live gates:
  `--allow-public-live`, `--ack-credentialed-wifi`,
  `--ack-public-exposure`, native confirm token, and public confirm token.
- Kept helper token delivery off the process command line by invoking the runner
  with tokens assigned in-process.
- Added resolver handling:
  native DHCP `/cache/a90-wifi/resolv.conf` first, chroot existing resolver
  second, host resolver fallback third.  Host resolver contents are sent via SSH
  stdin and recorded only as source/count metadata.
- Added loopback bring-up before D-public local smoke, fixing the observed
  `bind: Cannot assign requested address` failure when `lo` was down.
- Added bounded public smoke retry after quick Tunnel URL observation.
- Hardened process cleanup patterns to avoid `pkill -f` matching the shell
  command itself.

## Validation

Static:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py \
  tests/test_server_distro_wsta42_native_uplink_dpublic_tunnel.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
  python3 -m unittest tests.test_server_distro_wsta42_native_uplink_dpublic_tunnel
```

Result: `6 tests`, `OK`.

Precondition:

- WSTA28 reboot/materialization gate passed immediately before the final WSTA42
  run.
- Run dir:
  `workspace/private/runs/server-distro/wsta42-reboot-materialization-public-retry-20260704T082500Z`
- Nested WSTA27 result: `wsta27-materialization-scan-gate-pass`.
- Direct native scan: `scan_engine_ok=true`, `scan_has_bss=true`,
  `scan_result_count=12`, `trigger_rc=0`, `trigger_errno=0`.
- Post-reboot health: `selftest fail=0`.

Live WSTA42:

- Run dir:
  `workspace/private/runs/server-distro/wsta42-native-uplink-dpublic-live-public-retry-20260704T083000Z`
- Decision: `wsta42-native-uplink-dpublic-tunnel-pass`.
- Resident native support: pass on V3394 lineage.
- Native uplink: `native_uplink_confirmed=true`.
- Route gate: `default_route_wlan0=true`.
- Resolver gate: `resolver_ready=true`, `source=host-resolver`,
  `nameserver_count=2`, values redacted.
- Local smoke: `local_smoke_ok=true`, `loopback_up_rc=0`,
  `http_get_rc=0`, marker body length `80`.
- Quick Tunnel: `tunnel_url_observed=true`, public URL value redacted.
- Host public smoke: passed on attempt `3`, `http_status=200`,
  `marker_ok=true`, `service_ok=true`,
  `public_exposure_marker_ok=true`, `url_redacted=true`.
- Cleanup: D-public processes removed, service stopped, helper cleaned,
  chroot/dropbear/loop absent, final `selftest fail=0`.

Final manual health check after the pass:

- `wifi status`: `operstate=down`, `ipv4=none`,
  `default_route_present=0`, `supplicant.process_count=0`,
  `autoconnect.decision=wifi-autoconnect-disabled`.
- `selftest`: `fail=0`.

## Notes

- Native DHCP sometimes provides a default route but no DNS server
  (`nameserver_count=0`).  WSTA42 handles that by staging usable host resolver
  entries into the Debian chroot with the values redacted from public artifacts.
- Scan materialization can still go stale across same-boot Wi-Fi cleanup.  The
  final successful run used the WSTA28 reboot/materialization gate immediately
  before WSTA42.
- The proof is a quick Tunnel live gate, not a persistent always-on public
  posture.  Persistent server mode still needs its own public-live policy and
  cleanup/rollback discipline.
