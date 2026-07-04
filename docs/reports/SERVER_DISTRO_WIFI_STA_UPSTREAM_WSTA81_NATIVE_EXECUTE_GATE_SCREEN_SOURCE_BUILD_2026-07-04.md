# WSTA81 Native Execute Gate Screen Source Build

- Date: 2026-07-04
- Scope: display-only native WSTA operator screen for the WSTA80 execute gate
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta81-native-execute-gate-screen-source-build-pass`

## Summary

WSTA81 carries the WSTA80 default-off execute-gate state into the native
appliance display surface.  The `NETWORK` menu / `screenapp wsta` page now shows
that public exposure is still off, but the host-side operator pipeline has
reached the explicit WSTA58 live gate.

The screen remains display-only.  It does not run Wi-Fi connect, DHCP, tunnel
startup, native reboot, public smoke, userdata changes, switch-root, or flash
actions.

## Native Screen Text

```text
WSTA D-PUBLIC
STATE: PUBLIC_OFF EXEC-GATED
GATE: WSTA80 READY -> WSTA58
URL: REDACTED PRIVATE-RUN ONLY
NATIVE: DISPLAY-ONLY NO AUTOSTART
```

## Source Change

Updated:

- `workspace/public/src/native-init/a90_app_network.c`
- `tests/test_native_wsta_operator_screenapp_source.py`
- `workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py`
- `tests/test_server_distro_wsta24_native_wifi_uplink_client.py`
- `tests/test_server_distro_wsta26_scan_failure_diagnostic.py`

Added:

- `workspace/public/src/scripts/revalidation/build_native_init_boot_v3397_wsta_execute_gate_screen.py`
- `tests/test_build_native_init_boot_v3397_wsta_execute_gate_screen.py`

The WSTA host lineage gate now accepts:

```text
A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)
```

## Build Artifact

The V3397 source build completed without flashing:

```text
Boot image: workspace/private/inputs/boot_images/boot_linux_v3397_wsta_execute_gate_screen.img
Boot SHA256: 788e907cc3ffd24a6bc377e1751fed4921b15bc9974dba21333c736de454ff92
Init: A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)
Init binary SHA256: d88fef092972dcb669ca0b2550d017fa140bc5c291cd6ae6eebb3d3dd28fd9da
Helper SHA256: fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
Base boot: workspace/private/inputs/boot_images/boot_linux_v3396_wsta_persistent_state_screen.img
```

The generated native-init report is:

```text
docs/reports/NATIVE_INIT_V3397_WSTA_EXECUTE_GATE_SCREEN_SOURCE_BUILD_2026-07-04.md
```

Required strings were found in the V3397 init binary:

```text
A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)
0.11.153
NATIVE: DISPLAY-ONLY NO AUTOSTART
GATE: WSTA80 READY -> WSTA58
STATE: PUBLIC_OFF EXEC-GATED
doomgeneric-private-link-v3397-wsta-execute-gate-screen
```

## Safety

- No boot image was flashed.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The screenapp path remains read-only display.
- The source test asserts the WSTA screen block has no `a90_wifi_cmd`,
  `a90_wifi_scan_collect`, `a90_wifi_ping_collect`, `cloudflared`,
  `trycloudflare`, `connect`, or `native_init_flash.py`.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Private build artifacts remain under `workspace/private/`.

## Validation

Compile check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_native_init_boot_v3397_wsta_execute_gate_screen.py
```

Result: pass

Focused source tests:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_native_wsta_operator_screenapp_source \
  tests.test_build_native_init_boot_v3397_wsta_execute_gate_screen \
  tests.test_server_distro_wsta24_native_wifi_uplink_client \
  tests.test_server_distro_wsta26_scan_failure_diagnostic -v
```

Result: `Ran 16 tests ... OK`

Native/WSTA lineage regression:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_native_wsta_operator_screenapp_source \
  tests.test_build_native_init_boot_v3396_wsta_persistent_state_screen \
  tests.test_build_native_init_boot_v3397_wsta_execute_gate_screen \
  tests.test_server_distro_wsta24_native_wifi_uplink_client \
  tests.test_server_distro_wsta26_scan_failure_diagnostic -v
```

Result: `Ran 19 tests ... OK`

V3397 source build:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_native_init_boot_v3397_wsta_execute_gate_screen.py
```

Result: pass

## Next

The WSTA execute gate is now represented in the native appliance UI source and
the V3397 boot image is built, but it has not been flashed or displayed live.
Next options are a bounded V3397 flash/hot-reload display proof, or an
explicitly selected WSTA80/WSTA58 live proof with fresh private tokens.
