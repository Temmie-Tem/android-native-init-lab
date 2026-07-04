# Server Distro Wi-Fi STA Upstream WSTA40/WSTA41 Materialization Confirmed Autoconnect Pass

- Date: `2026-07-04`
- Decision: `wsta25-confirmed-autoconnect-live-pass`
- Resident under test: `A90 Linux init 0.11.150 (v3394-wifi-wpa-failure-detail)`
- WSTA40 evidence:
  `workspace/private/runs/server-distro/wsta40-reboot-materialization-v3394-20260704T053537Z/wsta28_result.json`
- WSTA41 evidence:
  `workspace/private/runs/server-distro/wsta41-confirmed-autoconnect-after-materialization-20260704T053848Z/wsta25_result.json`

## Scope

WSTA40 reuses the no-flash reboot materialization gate on resident V3394, then WSTA41
reruns the credential-gated WSTA25 confirmed autoconnect path after WSTA38/WSTA39 fixed
the stale profile material.  This closes the native STA uplink path through association,
WPA completion, DHCP, default-route presence, and resolver materialization.  It still
does not run external ping or public tunnel publishing.

## Source Changes

Updated:

- `workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py`
- `tests/test_server_distro_wsta28_reboot_materialization_gate.py`

The WSTA28 reboot gate now accepts the supported native uplink build list instead of
hard-coding only V3387, and its post-reboot health summary records
`contains_supported_native`.  This let the same materialization gate run against the
current V3394 resident without weakening the explicit native-reboot live gate.

## WSTA40 Reboot Materialization

WSTA40 ran with the explicit native-reboot live flag and no boot flash:

- `decision=wsta28-reboot-materialization-scan-gate-pass`
- `checks.explicit_live_gate=true`
- `checks.post_reboot_health=true`
- `checks.wsta27_after_reboot_pass=true`
- post-reboot version contained a supported native uplink build
- nested WSTA27 `decision=wsta27-materialization-scan-gate-pass`
- before materialization: `wlan0_present=0`, no default route, no supplicant process
- materialization probe: `decision=softap-iftype-probe-pass`
- `wlan0_wait_elapsed_ms=106870`
- `link_up_rc=0`
- `link_up_errno=0`
- `ap_iftype_add_rc=0`
- `ap_iftype_cleanup_ok=1`
- scan: `decision=wifi-scan-pass`
- `scan_result_count=12`
- `scan_engine_ok=true`
- `scan_has_bss=true`
- `trigger_rc=0`
- `trigger_errno=0`
- autoconnect remained disabled during the materialization gate

Interpretation: the V3394 resident can recover the stale WLAN state through the same
bounded reboot/materialization gate used earlier for V3387.

## WSTA41 Confirmed Autoconnect

After WSTA40 restored a green scan precondition, Codex explicitly enabled native
autoconnect and reran the WSTA25 confirmed-live runner with the confirm token redacted
from public artifacts.  The run passed:

- top-level `decision=wsta25-confirmed-autoconnect-live-pass`
- helper response `decision=wifi-uplink-service-autoconnect-pass`
- `autoconnect_decision=wifi-autoconnect-pass`
- `connect_diag_decision=wifi-connect-carrier-up`
- `connect_rc=0`
- `dhcp_rc=0`
- `final_rc=0`
- `carrier_up=1`
- `connect_carrier_wait_rc=0`
- `connect_carrier_up_at_wait=1`
- `connect_ctrl_status_wpa_state=COMPLETED`
- `default_route_present=1`
- `nameserver_count=2`
- `external_ping_execution=0`
- `public_tunnel=0`
- `secret_values_logged=0`

Interpretation: WSTA37's `WRONG_KEY` blocker was removed by credential material
restaging, and the native uplink service can now complete confirmed STA autoconnect
through DHCP on V3394 when it starts from the reboot/materialization scan-green state.

## Cleanup

After WSTA41, Codex restored the persistent state:

- `wifi autoconnect disable` returned `decision=wifi-autoconnect-disabled`
- `wifi cleanup` returned `decision=wifi-cleanup-done`
- follow-up `wifi status` showed no IPv4, no default route, no resolver file, no ctrl
  socket, and `supplicant.process_count=0`
- final `selftest` returned `pass=12`, `warn=1`, `fail=0`

## Safety

No forbidden partition was touched.  WSTA40 used a native reboot only; WSTA41 used the
existing credential-gated helper path.  No boot flash, switch-root, external ping,
public tunnel, raw credential logging, SSID, PSK, BSSID, raw MAC, raw IP, gateway, DNS
server value, public URL, or confirm-token value is recorded in public artifacts.  Raw
transcripts remain under `workspace/private/`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py tests/test_server_distro_wsta28_reboot_materialization_gate.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_wsta28_reboot_materialization_gate`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py --allow-native-reboot --run-dir workspace/private/runs/server-distro/wsta40-reboot-materialization-v3394-20260704T053537Z`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py --allow-confirmed-live --ack-credentialed-wifi --confirm-token <redacted> --skip-pre-confirm-scan-gate --service-lifetime-ms 360000 --confirmed-timeout-sec 300`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect disable`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi cleanup`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`

## Next

The native Wi-Fi STA uplink path is now proven through DHCP.  The next rung can retry
D-public/public tunnel exposure over this STA uplink, but only behind the existing
explicit public-live gates and with the same credential redaction policy.
