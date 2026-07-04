# Server Distro Wi-Fi STA Upstream WSTA25 Confirmed Gate Source Pass

- Date: `2026-07-04`
- Decision: `wsta25-confirmed-autoconnect-gate-source-pass`
- Scope: host/source only
- Live resident requirement for any future run: V3387 or later with
  `a90-native-wifi-uplink-service-v1`

## Change

The Debian-side `/usr/local/bin/a90-native-wifi-uplink-client` now has a WSTA25
`autoconnect-confirmed` operation, but it remains fail-closed by default.

Confirmed autoconnect requires both environment gates before any request file is written:

- `A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED=1`
- `A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN` equal to the native uplink-service confirm token

Without both gates, the helper exits before creating `request`:

- missing allow gate: `native-wifi-uplink-client-confirmed-disabled`
- missing or wrong confirm token: `native-wifi-uplink-client-confirm-token-missing`

The ambiguous `confirmed-autoconnect` spelling remains denied, and direct `autoconnect`,
`connect`, `dhcp`, `ping`, and public tunnel operations remain denied before request write.

## Safety

This unit did not run a live confirmed autoconnect and did not supply the confirm token to the
device.  No association, DHCP, ping, routing, public tunnel, boot flash, switch-root, userdata touch,
or credential-value logging ran.

The helper does not print the confirm token in success or failure output.  The token appears only as
the request field value when both WSTA25 environment gates are already present.

## Validation

- `sh -n workspace/public/src/scripts/server-distro/a90_native_wifi_uplink_client.sh`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py tests/test_native_wifi_uplink_client_helper.py tests/test_prepare_wsta3_sta_rootfs.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_native_wifi_uplink_client_helper tests.test_prepare_wsta3_sta_rootfs tests.test_server_distro_debian_rootfs_builder tests.test_server_distro_wsta24_native_wifi_uplink_client`
  - `32 tests`, `OK`

Focused behaviors proved by tests:

- `autoconnect-confirmed` without the allow gate exits `77` and writes no request.
- `autoconnect-confirmed` with allow but without the exact confirm token exits `77` and writes no
  request.
- `autoconnect-confirmed` with both gates writes `op=autoconnect` plus `confirm=...`, accepts a
  redacted native `wifi-uplink-service-autoconnect-pass` response, and does not echo the token.
- dangerous direct operations remain denied before request write.
- rootfs staging metadata records the confirmed-autoconnect env gate and fail-closed policy.

## Next

The next live unit, if selected, must be explicit and credential-gated.  It should start from resident
V3387 or later, mount the Debian chroot, start native `wifi uplink-service`, run
`autoconnect-confirmed` with both environment gates, and stop immediately after collecting redacted
native response metadata.  DHCP/routing and public exposure should remain separate gates unless the
operator explicitly authorizes them for that same live unit.
