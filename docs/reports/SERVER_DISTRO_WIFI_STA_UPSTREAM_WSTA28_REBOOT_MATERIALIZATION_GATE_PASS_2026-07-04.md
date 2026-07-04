# Server Distro Wi-Fi STA Upstream WSTA28 Reboot Materialization Gate Pass

- Date: `2026-07-04`
- Decision: `wsta28-reboot-materialization-scan-gate-pass`
- Resident under test: `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`
- Runner: `workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py`
- Evidence JSON:
  `workspace/private/runs/server-distro/wsta28-reboot-materialization-gate-20260704T025013Z/wsta28_result.json`

## Scope

Prove the WSTA28 no-flash recovery gate for the stale WLAN state found by WSTA26 and WSTA27:

1. require an explicit native-reboot live flag;
2. send a native reboot without flashing;
3. reacquire the serial bridge and require V3387 health;
4. run WSTA27 materialization/scan gate after reboot;
5. stop below association.

No boot flash, switch-root, service connect request, successful association, DHCP, external ping, or
public tunnel action ran.

## Source Changes

Added:

- `workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py`
- `tests/test_server_distro_wsta28_reboot_materialization_gate.py`

The runner:

- blocks by default with `wsta28-blocked-explicit-native-reboot-allow-required`;
- requires `--allow-native-reboot` before sending reboot;
- reuses the resident-session warm reboot and bridge-health helpers;
- waits briefly after post-reboot health and retries nested WSTA27 once if it hits a transient native
  health read;
- runs nested WSTA27 with `--allow-materialization-live`;
- prints a public-safe summary by default and keeps raw transcripts private.

Focused tests pin the explicit reboot gate, nested WSTA27 argument mapping, classification, public
summary redaction, and the command surface: reboot is allowed only behind the explicit gate, while
connect, DHCP, ping, public tunnel, and flash paths remain absent.

## Live Result

Default dry run:

- Command: `python3 workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py`
- Return code: `2`
- Decision: `wsta28-blocked-explicit-native-reboot-allow-required`
- No device work ran.

Explicit live run:

- Command:
  `python3 workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py --allow-native-reboot`
- Decision: `wsta28-reboot-materialization-scan-gate-pass`
- Reboot send was accepted without waiting for an END marker.
- Post-reboot health passed:
  - `version` contained V3387;
  - `status` returned `rc=0 status=ok`;
  - `selftest` returned `fail=0`.

Nested WSTA27 after reboot:

- Decision: `wsta27-materialization-scan-gate-pass`
- Before materialization:
  - `wlan0_present=0`
  - `operstate=-`
  - `ipv4=none`
  - `default_route_present=0`
  - `supplicant.process_count=0`
- Materialization probe:
  - `decision=softap-iftype-probe-pass`
  - `wlan0_present=1`
  - `wlan0_wait_elapsed_ms=106866`
  - `link_up_rc=0`
  - `link_up_errno=0`
  - `ap_iftype_add_rc=0`
  - `ap_iftype_cleanup_ok=1`
- Native scan:
  - `decision=wifi-scan-pass`
  - `scan_result_count=11`
  - `scan_engine_ok=true`
  - `scan_has_bss=true`
  - `link_up_rc=1`
  - `link_up_errno=0`
  - `trigger_rc=0`
  - `trigger_errno=0`
- After materialization/scan:
  - `wlan0_present=1`
  - `operstate=down`
  - `ipv4=none`
  - `default_route_present=0`
  - `supplicant.process_count=0`

Post-live native selftest still passed with `fail=0`, and autoconnect remained disabled with
`decision=wifi-autoconnect-disabled`.

## Interpretation

WSTA28 closes the immediate stale-WLAN blocker.  Same-boot recovery failed in WSTA27, but a clean
native reboot followed by the known materialization gate restores the native scan engine on current
V3387.  The next confirmed-autoconnect attempt should start from this green scan gate; it should not
skip reboot/materialization when `wlan0` is present but down.

## Safety

No boot flash, switch-root, service connect request, successful association, DHCP lease, default
route, external ping, public tunnel, raw credential logging, SSID, PSK, BSSID, MAC, private IP,
gateway, DNS server, public URL, or confirm-token value is recorded in public artifacts.  Raw
transcripts remain under `workspace/private/`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py tests/test_server_distro_wsta28_reboot_materialization_gate.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_wsta28_reboot_materialization_gate`
  - `5 tests`, `OK`
- Default fail-closed dry run:
  - `python3 workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py`
  - `wsta28-blocked-explicit-native-reboot-allow-required`
- Explicit live run:
  - `python3 workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py --allow-native-reboot`
  - `wsta28-reboot-materialization-scan-gate-pass`
- Post-live:
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect status`
- `git diff --check`

## Next

The WSTA25 confirmed live path can be retried only after preserving this scan-green precondition.
The next unit should enable autoconnect explicitly, run the existing WSTA25 confirmed live runner, and
then restore autoconnect disabled afterward.  Public exposure remains separate.
