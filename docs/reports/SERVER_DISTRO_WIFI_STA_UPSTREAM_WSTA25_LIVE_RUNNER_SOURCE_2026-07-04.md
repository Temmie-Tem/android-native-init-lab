# Server Distro Wi-Fi STA Upstream WSTA25 Live Runner Source Pass

- Date: `2026-07-04`
- Decision: `wsta25-confirmed-autoconnect-live-runner-source-pass`
- Scope: host/source plus fail-closed runner dry run
- Runner: `workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py`

## Change

Added a WSTA25 live runner for the Debian-side confirmed-autoconnect path.  The runner is
fail-closed by default: without all live gates, it returns before bridge/device/chroot work and never
creates an autoconnect request.

Required live gates:

- `--allow-confirmed-live`
- `--ack-credentialed-wifi`
- `--confirm-token` matching the native uplink-service confirm token

If the gates are present, the runner still performs a redacted `status` request first and requires
native autoconnect readiness before sending `autoconnect-confirmed`.  The confirmed helper command is
sent over SSH stdin through a redacted script executor, so the result JSON records `input_redacted=1`
and does not store the confirm-token value in the command vector.

## Safety

This source unit did not run a live confirmed autoconnect and did not supply the confirm token to the
device.  The dry run stopped before device access with:

- `decision=wsta25-blocked-explicit-live-allow-required`
- `explicit_live_gate=false`
- `confirm_token_supplied=false`
- `confirm_token_matches=false`

No association, DHCP, routing, ping, public tunnel, boot flash, switch-root, userdata touch, or
credential-value logging ran.

The live runner keeps public tunnel and external ping out of scope.  DHCP/routing are native-config
gated and only reachable after explicit confirmed-live gates plus readiness checks.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py tests/test_server_distro_wsta25_confirmed_autoconnect_live.py tests/test_server_distro_wsta24_native_wifi_uplink_client.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_wsta25_confirmed_autoconnect_live tests.test_server_distro_wsta24_native_wifi_uplink_client tests.test_native_wifi_uplink_client_helper tests.test_prepare_wsta3_sta_rootfs tests.test_server_distro_debian_rootfs_builder`
  - `38 tests`, `OK`
- Fail-closed dry run:
  - `python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py`
  - process return code: `2`
  - decision: `wsta25-blocked-explicit-live-allow-required`
- `git diff --check`

Focused tests cover:

- explicit live gate blocking order;
- status readiness requiring profile present, profile valid, autoconnect enabled, and ready;
- confirmed response requiring redacted native owner/pass fields;
- classifier separation for gate, readiness, confirmed helper, and cleanup failures;
- redacted SSH script executor not storing stdin/token content in the command vector;
- source surface denying direct `wifi connect`, `wifi dhcp`, `wifi ping`, cloud tunnel, SSID, and PSK work.

## Next

The next live unit can run this runner only when the operator explicitly selects the credentialed
live gate.  If selected, start on resident V3387 or later, supply all WSTA25 gates, allow the runner
to verify redacted status readiness first, then collect only redacted confirmed-autoconnect response
metadata and final health.  Keep DHCP/routing result interpretation separate from public exposure,
and do not start a public tunnel unless a later explicit gate authorizes it.
