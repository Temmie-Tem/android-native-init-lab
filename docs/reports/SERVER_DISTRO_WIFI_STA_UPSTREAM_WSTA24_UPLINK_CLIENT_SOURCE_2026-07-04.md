# Server Distro Wi-Fi STA Upstream WSTA24 Uplink Client Source Pass

- Date: `2026-07-04`
- Decision: `wsta24-native-wifi-uplink-client-source-pass`
- Scope: host/source only
- Base live resident for next gate: `V3387`

## Change

Added `/usr/local/bin/a90-native-wifi-uplink-client` as a Debian-side client for the V3387 native
uplink-service file protocol.

The helper is deliberately distinct from `/usr/local/bin/a90-native-wifi-service-client`:

- allowed operations: `status`, `autoconnect-no-confirm`;
- `status` writes `op=status`;
- `autoconnect-no-confirm` writes `op=autoconnect` without any confirm token;
- confirmed autoconnect, connect, association, DHCP, ping, and public tunnel operations are denied
  before any request file is written;
- response output is allowlisted and omits profile label values;
- helper output always includes `native_wifi_uplink_client_secret_values_logged=0`.

The WSTA3 private rootfs preparer and the base Debian rootfs builder now stage the helper at
`usr/local/bin/a90-native-wifi-uplink-client`.

## Validation

- `sh -n workspace/public/src/scripts/server-distro/a90_native_wifi_uplink_client.sh`
- `py_compile`:
  - `workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py`
  - `workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py`
- Unit tests:
  - `tests.test_native_wifi_uplink_client_helper`
  - `tests.test_prepare_wsta3_sta_rootfs`
  - `tests.test_server_distro_debian_rootfs_builder`
- Result: `25 tests`, `OK`

No device flash, association, DHCP, ping, public tunnel, userdata, or switch-root action ran in this
source unit.

## Next

WSTA24 live gate: with resident V3387, mount the Debian chroot, temporarily stage or use the helper,
start native `wifi uplink-service`, run the Debian helper for `status` and `autoconnect-no-confirm`,
verify redaction and denial behavior, cleanup, and finish with `selftest fail=0`.
