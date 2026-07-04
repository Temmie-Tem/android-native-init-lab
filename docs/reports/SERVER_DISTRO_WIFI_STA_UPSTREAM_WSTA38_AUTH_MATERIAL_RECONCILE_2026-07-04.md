# Server Distro Wi-Fi STA Upstream WSTA38 Auth Material Reconcile

- Date: `2026-07-04`
- Decision: `wsta38-credential-material-consistent`
- Resident under test: `A90 Linux init 0.11.150 (v3394-wifi-wpa-failure-detail)`
- Runner: `workspace/public/src/scripts/server-distro/run_wsta38_auth_material_reconcile.py`
- Initial mismatch evidence:
  `workspace/private/runs/server-distro/wsta38-auth-material-reconcile-v2-20260704T052950Z/wsta38_result.json`
- Profile restage evidence:
  `workspace/private/runs/wifi/a90-wifi-profile-stage-wsta39-20260704T053035Z`
- Final redacted pass evidence:
  `workspace/private/runs/server-distro/wsta38-auth-material-reconcile-final-redacted-20260704T054900Z/wsta38_result.json`

## Scope

WSTA38 stops probing native transport mechanics and compares the credential material
used by three already-existing paths:

- the private host Wi-Fi env;
- the earlier known-good Debian WSTA7 supplicant config;
- the resident native profile secrets plus generated native supplicant config.

This unit is read-only except for the explicit profile restage step between the first
and second reconciliation runs.  WSTA38 itself does not associate, request DHCP, run
external ping, or open a public tunnel.  It records only lengths, formats, equality
booleans, and redacted file classes.

## Source Changes

Added:

- `workspace/public/src/scripts/server-distro/run_wsta38_auth_material_reconcile.py`
- `tests/test_server_distro_wsta38_credential_reconciliation.py`

The runner parses supplicant configs with structured metadata, computes the expected
native WPA-PSK hex via `hashlib.pbkdf2_hmac_sha1_4096_32`, compares equality without
printing secret values, and classifies stale device profile secrets before blaming
native PBKDF2 output.  Device profile paths are redacted to `<profile>` placeholders
so a profile label cannot leak through public stdout or JSON metadata.

## Initial Result

The first full reconciliation classified the WSTA37 `WRONG_KEY` result as stale native
device PSK material:

- `decision=wsta38-device-psk-secret-mismatch`
- host Wi-Fi env: present, owner-private, SSID length `8`, PSK length `11`
- WSTA7 known-good config: SSID length `8`, PSK length `11`
- resident device profile SSID secret length `8`
- resident device profile PSK secret length `10`
- `wsta7_ssid_matches_env=true`
- `wsta7_psk_matches_env=true`
- `device_ssid_secret_matches_env=true`
- `device_psk_secret_matches_env=false`
- `native_ssid_hex_matches_env=true`
- `native_psk_hex_matches_python_reference=false`
- `native_psk_hex_matches_device_secret_reference=true`
- `association_attempted=false`
- `dhcp_attempted=false`
- `ping_attempted=false`
- `public_tunnel=false`
- `secret_values_logged=0`

Interpretation: the native generated supplicant config was internally consistent with
the resident device PSK secret, but that resident PSK secret did not match the host
credential env or the WSTA7 known-good Debian config.  The blocker was stale profile
material, not native PBKDF2, control-socket handling, scan recovery, or AP mode.

## Restage And Final Result

Codex restaged the native Wi-Fi profile from the current private env using the existing
profile staging helper.  The staging run returned `decision=wifi-profile-stage-pass`
and `secret_values_logged=0`.

The final WSTA38 redacted run passed:

- `decision=wsta38-credential-material-consistent`
- `credential_material_consistent=true`
- `wsta7_ssid_matches_env=true`
- `wsta7_psk_matches_env=true`
- `device_ssid_secret_matches_env=true`
- `device_psk_secret_matches_env=true`
- `native_ssid_hex_matches_env=true`
- `native_psk_hex_matches_python_reference=true`
- `native_psk_hex_matches_device_secret_reference=true`
- device profile SSID secret length `8`
- device profile PSK secret length `11`
- native config SSID format `hex`
- native config PSK format `hex64`
- `association_attempted=false`
- `dhcp_attempted=false`
- `ping_attempted=false`
- `public_tunnel=false`
- `secret_values_logged=0`

## Safety

No boot flash, switch-root, association, DHCP lease, default-route assertion, external
ping, public tunnel, raw credential logging, SSID, PSK, BSSID, raw MAC, raw IP,
gateway, DNS server, public URL, or confirm-token value is recorded in public
artifacts.  Raw transcripts and private credential material remain under
`workspace/private/`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta38_auth_material_reconcile.py tests/test_server_distro_wsta38_credential_reconciliation.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_wsta38_credential_reconciliation`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/server-distro/run_wsta38_auth_material_reconcile.py --run-dir workspace/private/runs/server-distro/wsta38-auth-material-reconcile-final-redacted-20260704T054900Z`

## Next

With credential material reconciled, the next live rung may retry native confirmed
autoconnect only after restoring a green scan/materialization precondition.  Public
exposure remains a separate explicit live gate.
