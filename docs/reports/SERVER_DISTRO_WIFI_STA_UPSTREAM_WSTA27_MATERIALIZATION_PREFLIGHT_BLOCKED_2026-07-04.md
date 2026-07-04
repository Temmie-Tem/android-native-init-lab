# Server Distro Wi-Fi STA Upstream WSTA27 Materialization Preflight Blocked

- Date: `2026-07-04`
- Decision: `wsta27-blocked-materialization-preflight`
- Resident under test: `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`
- Runner: `workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py`
- Evidence JSON:
  `workspace/private/runs/server-distro/wsta27-materialization-preflight-20260704T024257Z/wsta27_result.json`

## Scope

Add and run the WSTA27 guard that must pass before another confirmed autoconnect live attempt.  The
guard is explicit-live-gated and remains below association: it may run the already-bounded native
iftype materialization probe, but it never sends a service connect request and never runs DHCP, ping,
or public exposure.

## Source Changes

Added:

- `workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py`
- `tests/test_server_distro_wsta27_materialization_preflight.py`

The runner:

- blocks by default with `wsta27-blocked-explicit-materialization-live-allow-required`;
- requires `--allow-materialization-live` before touching the device;
- verifies resident V3387, native selftest, and `wifi-autoconnect-disabled`;
- records redacted `wifi status`;
- runs `wifi softap iftype-probe <timeout_ms>` only when `wlan0` is not administratively up;
- runs a native scan window only if materialization/admin-up succeeds;
- prints only a public-safe summary by default while storing raw transcripts in private JSON.

Focused tests pin the explicit gate, iftype summary redaction, cleanup-sensitive probe pass
criteria, classification, public-summary redaction, and the absence of connect/DHCP/ping/tunnel/flash
command surfaces.

## Live Result

Default dry run:

- Command: `python3 workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py`
- Return code: `2`
- Decision: `wsta27-blocked-explicit-materialization-live-allow-required`
- No device work ran.

Explicit live run:

- Command:
  `python3 workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py --allow-materialization-live`
- Decision: `wsta27-blocked-materialization-preflight`
- Resident V3387 check passed.
- Baseline and final native selftest both passed with `fail=0`.
- Autoconnect remained disabled:
  - `autoconnect=0`
  - `decision=wifi-autoconnect-disabled`
- Redacted Wi-Fi status before and after preflight:
  - `wlan0_present=1`
  - `operstate=down`
  - `ipv4=none`
  - `default_route_present=0`
  - `supplicant.process_count=0`
  - `ctrl_socket.kind=missing`
- Materialization probe:
  - `decision=softap-iftype-probe-link-up-failed`
  - `wlan0_present=1`
  - `wlan0_wait_elapsed_ms=0`
  - `link_up_rc=-1`
  - `link_up_errno=22`
- Because materialization failed, the runner did not run the scan gate and did not send any confirmed
  autoconnect request.

## Interpretation

WSTA27 confirms that the current V3387 resident is in the stale WLAN state already described by WSTA7,
WSTA19, and WSTA26: `wlan0` exists but cannot be administratively brought up (`SIOCSIFFLAGS` returns
`EINVAL` / `link_up_errno=22`).  The safe materialization probe cannot recover this state in the same
boot.

The next meaningful unit is not another confirmed autoconnect attempt.  It is a controlled native
reboot/materialization gate: reboot cleanly without flashing, wait for V3387 bridge health, rerun the
WSTA27 materialization/scan gate, and only if scan passes consider re-entering the WSTA25 confirmed
live path.

## Safety

No boot flash, switch-root, service connect request, successful association, DHCP lease, default
route, external ping, public tunnel, raw credential logging, SSID, PSK, BSSID, MAC, private IP,
gateway, DNS server, public URL, or confirm-token value is recorded in public artifacts.  Raw
transcripts remain under `workspace/private/`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py tests/test_server_distro_wsta27_materialization_preflight.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_wsta27_materialization_preflight`
  - `6 tests`, `OK`
- Default fail-closed dry run:
  - `python3 workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py`
  - `wsta27-blocked-explicit-materialization-live-allow-required`
- Explicit live run:
  - `python3 workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py --allow-materialization-live`
  - `wsta27-blocked-materialization-preflight`
- Post-live:
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`
  - `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect status`
- `git diff --check`

## Next

WSTA28 should be a no-flash controlled reboot/materialization gate for V3387: reboot native init,
wait for bridge/version/selftest, confirm autoconnect remains disabled, rerun WSTA27, and stop unless
direct native scan passes.  Confirmed autoconnect remains parked until that scan gate is green.
