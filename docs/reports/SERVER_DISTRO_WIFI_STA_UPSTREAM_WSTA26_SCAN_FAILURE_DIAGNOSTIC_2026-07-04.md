# Server Distro Wi-Fi STA Upstream WSTA26 Scan Failure Diagnostic

- Date: `2026-07-04`
- Decision: `wsta26-direct-native-scan-blocked`
- Resident under test: `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`
- Runner: `workspace/public/src/scripts/server-distro/run_wsta26_scan_failure_diagnostic.py`
- Evidence JSON:
  `workspace/private/runs/server-distro/wsta26-scan-failure-diagnostic-20260704T023820Z/wsta26_result.json`

## Scope

Diagnose the WSTA25 confirmed-autoconnect scan failure without sending another confirmed request.
This unit stays below association and only checks resident health, fail-closed autoconnect state,
redacted Wi-Fi status, and a bounded native `wifi scan` window.

No boot flash, switch-root, chroot, confirmed autoconnect, association, DHCP, ping, or public tunnel
action ran.

## Source Changes

Added a WSTA26 no-flash live runner:

- `workspace/public/src/scripts/server-distro/run_wsta26_scan_failure_diagnostic.py`

The runner records full command transcripts only in private JSON and prints a public-safe summary by
default.  The summary omits raw scan text and keeps only operational fields such as scan decision,
scan count, link-up errno, autoconnect disabled state, redacted link status, and safety flags.

Added focused tests:

- `tests/test_server_distro_wsta26_scan_failure_diagnostic.py`

The tests pin V3387 detection, redacted status summaries, classification, public-summary redaction,
and the no-association/no-DHCP/no-public-tunnel command surface.

## Live Result

Preconditions:

- Resident check passed for `0.11.143` / `v3387-wifi-uplink-service-redacted`.
- Baseline selftest passed with `fail=0`.
- Autoconnect was disabled:
  - `decision=wifi-autoconnect-disabled`
  - `autoconnect=0`
  - `config_present=1`
  - `config_valid=1`
  - `profile_valid=1`
  - `dhcp=1`
  - `external_ping=0`
  - `secret_values_logged=0`

Redacted Wi-Fi status before and after the scan window:

- `wlan0_present=1`
- `operstate=down`
- `ipv4=none`
- `default_route_present=0`
- `supplicant.process_count=0`
- `ctrl_socket.kind=missing`
- `decision=wifi-status-wlan0-present`

Direct native scan window:

- Attempts completed: `4`
- All attempts returned `decision=wifi-scan-link-up-failed`.
- All attempts had `link_up_rc=-1` and `link_up_errno=22`.
- `scan_engine_ok=false`
- `scan_has_bss=false`

Final native selftest still passed with `fail=0`.

## Interpretation

WSTA26 narrows the WSTA25 blocker.  The failure is not limited to Debian helper plumbing, confirm-token
delivery, request-file handoff, or the native `wifi uplink-service` status path.  In the current
post-WSTA25 resident state, direct native `wifi scan` also fails before nl80211 trigger, at the
administrative link-up step for `wlan0`.

This matches the earlier stale WLAN state observed in WSTA7 and WSTA19: `wlan0` can exist with
`flags=0x1002` / `operstate=down`, while `SIOCSIFFLAGS` returns `EINVAL` (`link_up_errno=22`).  WSTA19
showed the reliable precondition was a fresh native boot plus WSTA2 materialization/iftype-probe
before scan; after that, native scans passed before and during the Debian chroot.

## Safety

No successful association, DHCP lease, route, external ping, public tunnel, raw credential logging,
SSID, PSK, BSSID, MAC, private IP, gateway, DNS server, public URL, or confirm-token value is recorded
in public artifacts.  Raw transcripts remain under `workspace/private/`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta26_scan_failure_diagnostic.py tests/test_server_distro_wsta26_scan_failure_diagnostic.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_wsta26_scan_failure_diagnostic`
  - `5 tests`, `OK`
- `python3 workspace/public/src/scripts/server-distro/run_wsta26_scan_failure_diagnostic.py --wsta25-result workspace/private/runs/server-distro/wsta25-confirmed-autoconnect-live-20260704T022920Z/wsta25_result.json`
  - result: `wsta26-direct-native-scan-blocked`
- Post-live:
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status`
- `git diff --check`

## Next

WSTA27 should restore the known-good materialization precondition on current V3387 before reattempting
confirmed autoconnect.  The bounded first step is source support for a WSTA27 preflight that runs a
safe native materialization/scan gate, requires direct native scan success, and only then permits the
existing WSTA25 confirmed live runner.  Do not send another confirmed request until that scan gate
passes.
