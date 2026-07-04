# Server Distro Wi-Fi STA Upstream WSTA24 Uplink Client Live Pass

- Date: `2026-07-04`
- Decision: `wsta24-native-wifi-uplink-client-pass`
- Resident under test: `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`
- Debian helper: `/usr/local/bin/a90-native-wifi-uplink-client`
- Evidence JSON: `workspace/private/runs/server-distro/wsta24-native-wifi-uplink-client-20260704T020009Z/wsta24_result.json`

## Scope

Prove the Debian-side uplink-service helper against resident V3387 without flashing and without
credentials or public exposure:

- require resident V3387 and clean native health;
- ensure the SD-backed Debian rootfs image matches the current expected SHA;
- mount the Debian chroot and start temporary key-only dropbear;
- stage the current helper in the mounted Debian rootfs;
- start native `wifi uplink-service` in a chroot-visible service directory;
- run helper `status` and `autoconnect-no-confirm` from Debian;
- stop the native service, remove temporary helper staging, cleanup chroot/dropbear/loop state, and
  finish with native `selftest fail=0`.

No boot flash, switch-root, userdata touch, Wi-Fi association, confirm-token supply, DHCP, ping, or
public tunnel action ran.

## Preflight

- Starting resident: `0.11.143` / `v3387-wifi-uplink-service-redacted`
- Baseline native selftest: `pass=12 warn=1 fail=0`
- Hardware contract command passed.
- Local Debian image SHA256:
  `210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc`
- Remote SD image initially had a stale SHA and was reinstalled through the existing local USB/NCM
  transfer path.
- Remote SD image after reinstall matched:
  `210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc`

## Debian Chroot

- Debian SSH marker passed.
- Debian version observed: `12.14`
- Stage marker present.
- Temporary key-only dropbear was used.
- Helper staging marker: `A90WSTA24_HELPER_STAGED`

## Native Uplink Service

Service start:

- Command surface: `wifi uplink-service start`
- Version: `a90-native-wifi-uplink-service-v1`
- Result: `wifi-uplink-service-start-pass`
- Start elapsed: `0.595s`

Helper `status` from Debian:

- Helper decision: `native-wifi-uplink-client-pass`
- Native decision: `wifi-uplink-service-status-pass`
- `version=a90-native-wifi-uplink-service-v1`
- `owner=native-init`
- `credentials=0`
- `connect=0`
- `dhcp_routing=observed-only`
- `public_tunnel=0`
- `secret_values_logged=0`
- Elapsed: `1.136s`

The status path emitted profile-present booleans rather than profile label values.

Helper `autoconnect-no-confirm` from Debian:

- Helper decision: `native-wifi-uplink-client-pass`
- Native result: `rc=-13`
- Native decision: `wifi-uplink-service-confirm-required`
- `connect=confirm-gated`
- `dhcp_routing=config-gated`
- `external_ping_execution=0`
- `public_tunnel=0`
- `secret_values_logged=0`
- Elapsed: `1.131s`

No confirm token was supplied, so native init denied the request before connect/DHCP.

## Cleanup

- Native service stop result: `wifi-uplink-service-stop-pass`
- Temporary helper staging was removed.
- Chroot mount absent after cleanup.
- Loop node absent after cleanup.
- Dropbear absent after postcheck.
- Final resident still V3387.
- Final selftest: `pass=12 warn=1 fail=0`

One cleanup transcript line reported dropbear still present immediately before the delayed postcheck,
but the bounded postcheck observed dropbear absent and the final runner check passed.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py tests/test_server_distro_wsta24_native_wifi_uplink_client.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_wsta24_native_wifi_uplink_client`
  - `4 tests`, `OK`
- `git diff --check`
- Live runner:
  - `python3 workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py`
  - Result: `wsta24-native-wifi-uplink-client-pass`

## Next

The remaining Wi-Fi upstream rung is the credential-gated confirmed autoconnect/DHCP path.  That must
be a separate explicit unit with the confirm token, private credential handling, rollback/cleanup
rules, and no public exposure unless separately authorized.  Until that unit is selected, keep
confirmed association, DHCP, ping, and public tunnel execution parked.
