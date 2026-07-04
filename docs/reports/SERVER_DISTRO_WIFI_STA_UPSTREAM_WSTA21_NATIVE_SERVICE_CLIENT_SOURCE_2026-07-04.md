# Server Distro Wi-Fi STA Upstream WSTA21 Native Service Client Source Pass

- Date: `2026-07-04`
- Decision: `wsta21-native-wifi-service-client-source-pass`
- Device action: `none`
- Based on live boundary: `WSTA20`, resident candidate `A90 Linux init 0.11.141 (v3385-wifi-service-boundary)`

## Scope

WSTA21 factors the WSTA20 request/response file protocol into a reusable Debian-side helper:

- Debian writes an atomic `request` file with `seq`, `op=status|scan`, and `scan_delay_ms`.
- Native init remains the Wi-Fi owner and is expected to write the `response`.
- The helper accepts only `status` and `scan`.
- `connect`, association, DHCP, ping, and public tunnel operations are rejected before a request file is written.
- The helper filters response output to known redacted keys and requires `owner=native-init`.

## Source Changes

- Added `workspace/public/src/scripts/server-distro/a90_native_wifi_service_client.sh`.
- Staged the helper into prepared WSTA rootfs copies as `/usr/local/bin/a90-native-wifi-service-client`.
- Staged the helper into newly built Debian rootfs images and recorded it in `/etc/a90-server-distro-stage`.
- Added host tests for both staging paths and a subprocess roundtrip test that simulates the native service response.

## Validation

Commands run:

```text
sh -n workspace/public/src/scripts/server-distro/a90_native_wifi_service_client.sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py tests/test_prepare_wsta3_sta_rootfs.py tests/test_server_distro_debian_rootfs_builder.py tests/test_native_wifi_service_client_helper.py
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_prepare_wsta3_sta_rootfs tests.test_server_distro_debian_rootfs_builder tests.test_native_wifi_service_client_helper
```

Result:

```text
Ran 23 tests in 1.031s
OK
```

## Safety

- No flash, reboot, userdata write, association, DHCP, ping, API, public tunnel, or switch-root action ran.
- The helper does not consume Wi-Fi credentials.
- Dangerous operations are denied before the request file is published.
- Response printing is allowlisted; raw SSID, PSK, BSSID, MAC, DHCP lease, or concrete address fields are not emitted by the helper.

## Next

WSTA22 live gate should run the helper inside the Debian chroot while V3385 native init owns the Wi-Fi service:

1. health-check the current resident;
2. run WSTA2 materialization if needed;
3. mount the SD-backed Debian chroot and start key-only SSH;
4. start native `wifi service`;
5. execute `/usr/local/bin/a90-native-wifi-service-client status` and `scan` from Debian;
6. verify helper decisions, redaction, cleanup, and final `selftest fail=0`.

Keep connect/association/DHCP/public tunnel as a separate gated native-owned service rung.
