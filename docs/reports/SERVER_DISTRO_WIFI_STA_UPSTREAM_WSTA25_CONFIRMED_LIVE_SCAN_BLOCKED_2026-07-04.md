# Server Distro Wi-Fi STA Upstream WSTA25 Confirmed Live Scan Blocked

- Date: `2026-07-04`
- Decision: `wsta25-blocked-helper-confirmed-autoconnect`
- Resident under test: `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`
- First live evidence JSON:
  `workspace/private/runs/server-distro/wsta25-confirmed-autoconnect-live-20260704T022558Z/wsta25_result.json`
- Confirmed live evidence JSON:
  `workspace/private/runs/server-distro/wsta25-confirmed-autoconnect-live-20260704T022920Z/wsta25_result.json`

## Scope

Run the explicit WSTA25 credential-gated confirmed-autoconnect live path against resident V3387
without boot flashing, switch-root, public tunnel exposure, or external ping.

The live path mounted the SD-backed Debian rootfs, started temporary key-only dropbear, staged the
current Debian helper, started native `wifi uplink-service`, queried redacted status, and only sent
`autoconnect-confirmed` after the native redacted status reported autoconnect ready.

## Result

First live run:

- Decision: `wsta25-blocked-autoconnect-not-ready`
- Native helper status passed.
- Autoconnect config was present and valid, but `autoconnect_enabled=0` and `autoconnect_ready=0`.
- The confirmed helper was skipped with reason `autoconnect-not-ready`.
- Cleanup passed and final native selftest remained `fail=0`.

Enable-only preparation:

- `wifi autoconnect enable` returned `decision=wifi-autoconnect-enabled`.
- Follow-up status returned `decision=wifi-autoconnect-ready`.
- This step only changed the native autoconnect config; it did not run connect, DHCP, ping, or public
  exposure.

Confirmed live run:

- Redacted helper status before the confirmed request passed:
  - `autoconnect_config_decision=wifi-autoconnect-ready`
  - `autoconnect_enabled=1`
  - `autoconnect_ready=1`
  - `config_profile_present=1`
  - `profile_valid=1`
  - `external_ping_execution=0`
  - `public_tunnel=0`
  - `secret_values_logged=0`
- The Debian helper sent the confirmed request through the redacted stdin executor:
  - command vector did not include the confirm token;
  - `input_redacted=True`;
  - helper return code was `10`.
- Native confirmed-autoconnect failed at scan:
  - `native_wifi_uplink_client_decision=native-wifi-uplink-client-native-failed`
  - `decision=wifi-uplink-service-autoconnect-failed`
  - `autoconnect_decision=wifi-autoconnect-scan-failed`
  - `rc=-22`
  - `connect_rc=-22`
  - `dhcp_rc=0`
  - `final_rc=-22`
  - `carrier_up=0`
  - `default_route_present=0`
  - `external_ping_execution=0`
  - `public_tunnel=0`
  - `secret_values_logged=0`

After the live gate, `wifi autoconnect disable` restored the native autoconnect config to
`decision=wifi-autoconnect-disabled`.

## Cleanup And Health

- Native `wifi uplink-service stop` returned `wifi-uplink-service-stop-pass`.
- Temporary Debian helper staging was removed.
- Chroot mount was absent after cleanup/postcheck.
- Loop node was absent after cleanup/postcheck.
- Dropbear was absent after postcheck.
- Final resident still reported V3387.
- Final native selftest after cleanup and autoconnect-disable remained `pass=12 warn=1 fail=0`.
- Final redacted `wifi status` after cleanup reported `wlan0_present=1`, `operstate=down`,
  `ipv4=none`, `default_route_present=0`, `supplicant.process_count=0`,
  `ctrl_socket.kind=missing`, and `decision=wifi-status-wlan0-present`.

## Safety

No boot flash, switch-root, userdata formatter action, public tunnel, external ping, successful
association, DHCP lease, default route, raw credential logging, or confirm-token logging occurred.
The confirmed request was sent only after the explicit live gates and redacted readiness gate passed.

Public artifacts intentionally omit SSID, PSK, confirm token, BSSID, MAC, DHCP lease, private IP,
gateway, DNS server, and public URL values.

## Validation

- Live runner:
  - `python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py --allow-confirmed-live --ack-credentialed-wifi --confirm-token <redacted>`
  - first result: `wsta25-blocked-autoconnect-not-ready`
  - confirmed result: `wsta25-blocked-helper-confirmed-autoconnect`
- Post-live health:
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py version`
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect disable`
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect status`
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status`
- `git diff --check`

## Next

WSTA26 should diagnose the scan failure before reattempting confirmed autoconnect.  Keep the next
unit bounded to scan/link-state evidence: compare direct native `wifi scan` behavior with the
uplink-service autoconnect path, capture redacted `wpa_supplicant`/`wlan0` state, and avoid confirmed
connect, DHCP, external ping, and public exposure until the scan blocker is explained.
