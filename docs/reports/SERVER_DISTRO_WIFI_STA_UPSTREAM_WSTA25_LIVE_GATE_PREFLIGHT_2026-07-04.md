# Server Distro Wi-Fi STA Upstream WSTA25 Live Gate Preflight Pass

- Date: `2026-07-04`
- Decision: `wsta25-credentialed-live-preflight-pass`
- Scope: host-only credential/live-gate preflight
- Script: `workspace/public/src/scripts/server-distro/prepare_wsta25_live_gate_preflight.py`
- Evidence JSON: `workspace/private/runs/server-distro/wsta25-credentialed-live-preflight-20260704T022247Z/wsta25_preflight.json`

## Scope

Prepare the next WSTA25 credentialed live run without contacting the device or starting association.
The preflight validates private Wi-Fi credential file metadata, verifies the WSTA25 runner surface,
and emits a redacted command template for the later explicit live gate.

No SSID, PSK, confirm-token, BSSID, MAC, DHCP lease, private IP, public URL, or raw secret value is
written to the public report or result JSON.

## Result

Private Wi-Fi env metadata:

- file exists: `true`
- owner-private mode: `true`
- SSID present: `true`
- PSK present: `true`
- SSID byte length: `8`
- PSK length: `11`
- PSK format: `passphrase`
- `secret_values_logged=0`

Runner surface:

- WSTA25 live runner exists.
- Explicit live gates are present.
- Confirm-token arg is present.
- Status readiness gate is present.
- Redacted SSH stdin executor is present.
- Direct `wifi connect`, `wifi dhcp`, `wifi ping`, external ping, and public tunnel work are absent.

Default dry run:

- command: `python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py`
- return code: `2`
- decision: `wsta25-blocked-explicit-live-allow-required`

The redacted command template includes `--allow-confirmed-live`, `--ack-credentialed-wifi`, and
`--confirm-token <redacted:A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN>`.

## Safety

This unit was host-only except for reading private credential metadata locally.  It did not contact
the device, did not mount the Debian chroot, did not supply the confirm token to the device, and did
not run live confirmed autoconnect.

No association, DHCP, routing, ping, public tunnel, boot flash, switch-root, userdata touch, or
credential-value logging ran.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/prepare_wsta25_live_gate_preflight.py tests/test_prepare_wsta25_credentialed_live_preflight.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_prepare_wsta25_credentialed_live_preflight`
  - `6 tests`, `OK`
- Larger WSTA helper/rootfs/runner regression:
  - `44 tests`, `OK`
- Live-gate preflight:
  - `python3 workspace/public/src/scripts/server-distro/prepare_wsta25_live_gate_preflight.py`
  - result: `wsta25-credentialed-live-preflight-pass`
- `git diff --check`

## Next

The next step can be the explicit WSTA25 credentialed live run.  It should use the WSTA25 live runner
with all live gates, let the runner block if native redacted status says autoconnect is not ready, and
collect only redacted confirmed-autoconnect metadata plus final native health.  Public exposure remains
a separate later gate.
