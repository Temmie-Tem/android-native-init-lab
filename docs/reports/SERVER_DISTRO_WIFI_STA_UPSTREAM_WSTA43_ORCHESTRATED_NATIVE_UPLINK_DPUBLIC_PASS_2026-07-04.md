# WSTA43 Orchestrated Native-Owned STA Uplink + D-public Pass

Date: 2026-07-04 KST

## Verdict

PASS.  WSTA43 turns the WSTA42 live proof into a reproducible one-command
orchestrated gate by running the WSTA28 reboot/materialization scan-green
precondition and then the WSTA42 native-owned STA uplink + Debian D-public quick
Tunnel gate.

No boot flash, switch-root, userdata formatter action, forbidden partition write,
external ping, raw credential logging, confirm-token logging, DNS-value logging,
or committed public URL occurred.  The generated public URL stayed private-only.

## Source Changes

- Added `workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py`.
- Added focused tests in
  `tests/test_server_distro_wsta43_orchestrated_native_uplink_dpublic.py`.
- WSTA43 requires all live gates before doing device work:
  `--allow-orchestrated-live`, `--allow-native-reboot`,
  `--allow-public-live`, `--ack-credentialed-wifi`,
  `--ack-public-exposure`, native confirm token, and public confirm token.
- WSTA43 runs WSTA28 first and stops before any public tunnel attempt unless
  `wsta28-reboot-materialization-scan-gate-pass` is proven.
- WSTA43 then runs WSTA42 with autoconnect enabled only under the explicit gates.
- The public summary preserves only redacted metadata and omits the public URL
  value, DNS values, credential values, and token values.

## Validation

Static:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py \
  tests/test_server_distro_wsta43_orchestrated_native_uplink_dpublic.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
  python3 -m unittest tests.test_server_distro_wsta43_orchestrated_native_uplink_dpublic
```

Result: `5 tests`, `OK`.

Fail-closed dry run:

- Run dir:
  `workspace/private/runs/server-distro/wsta43-default-gate-20260704T085000Z`
- Decision: `wsta43-blocked-explicit-orchestrated-live-allow-required`.
- No device step ran.

Live WSTA43:

- Run dir:
  `workspace/private/runs/server-distro/wsta43-orchestrated-live-20260704T085500Z`
- Decision: `wsta43-orchestrated-native-uplink-dpublic-pass`.
- Gates: explicit orchestrated live, native reboot, public live, credentialed
  Wi-Fi ack, public-exposure ack, native confirm token, and public confirm token
  all passed.

Nested WSTA28:

- Decision: `wsta28-reboot-materialization-scan-gate-pass`.
- Reboot send accepted with no transport error.
- Post-reboot health passed with supported V3394 lineage and `selftest fail=0`.
- Nested WSTA27 decision: `wsta27-materialization-scan-gate-pass`.
- Iftype probe: `softap-iftype-probe-pass`, `wlan0_wait_elapsed_ms=98862`,
  `link_up_rc=0`, `ap_iftype_add_rc=0`, `ap_iftype_cleanup_ok=1`.
- Direct native scan: `wifi-scan-pass`, `scan_result_count=12`,
  `scan_engine_ok=true`, `scan_has_bss=true`, `trigger_rc=0`,
  `trigger_errno=0`.

Nested WSTA42:

- Decision: `wsta42-native-uplink-dpublic-tunnel-pass`.
- Native uplink confirmed: pass.
- Route gate: `default_route_wlan0=true`.
- Resolver gate: `resolver_ready=true`, `source=native-dhcp`,
  `nameserver_count=2`, values redacted.
- Local D-public smoke: `local_smoke_ok=true`, `loopback_up_rc=0`,
  `http_get_rc=0`.
- Quick Tunnel: `url_observed=true`, public URL value redacted.
- Host public smoke: passed on attempt `2`, `http_status=200`,
  `marker_ok=true`, `service_ok=true`,
  `public_exposure_marker_ok=true`, `url_redacted=true`.
- Cleanup: D-public processes stopped, native service stopped, helper cleaned,
  chroot/dropbear/loop postcheck absent, final `selftest fail=0`.

Final health after WSTA43:

- `wifi status`: `operstate=down`, `ipv4=none`,
  `default_route_present=0`, `supplicant.process_count=0`,
  `autoconnect.decision=wifi-autoconnect-disabled`,
  `secret_values_logged=0`.
- `selftest`: `fail=0`.

## Notes

- WSTA43 closes the immediate reproducibility gap from WSTA42: the scan-green
  precondition is no longer an operator-memory step.
- This is still a gated quick-Tunnel proof, not a persistent always-on public
  appliance posture.
- The next rung should integrate the same native-owned uplink and Debian
  service/HUD sequence into the appliance workflow with default public exposure
  still off.
