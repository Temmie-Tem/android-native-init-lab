# WSTA66 Persistent Session Retire Source

- Date: 2026-07-04
- Scope: host-only WSTA persistent session retire marker
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta66-persistent-session-retire-pass`

## Summary

WSTA66 adds an explicit retire path for prepared persistent exposure sessions.
WSTA63/WSTA64/WSTA65 can prepare and classify a session as live-ready; WSTA66
lets the operator mark that private session as intentionally unused without
deleting artifacts or touching the device.

The retire marker is consumed by WSTA65.  When supplied, WSTA65 forces:

```text
session_state=RETIRED
ready_for_live=false
recommended_next_action=rerun-wsta63-then-wsta64-if-live-is-needed
```

This prevents an already prepared session from being accidentally reused after
the operator decides not to run live exposure.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta66_persistent_session_retire.py`
- `tests/test_server_distro_wsta66_persistent_session_retire.py`

Updated:

- `workspace/public/src/scripts/server-distro/run_wsta65_persistent_session_status.py`

WSTA66 is fail-closed until the operator supplies:

```text
--retire-session
--ack-retire-session
--wsta65-result-json workspace/private/runs/server-distro/<wsta65-run>/wsta65_result.json
```

It writes a private marker:

```text
wsta66_retire_marker.json
```

WSTA65 accepts the marker only if it is private, schema-valid, pass-marked,
points at the same WSTA64 result being queried, and contains no raw public URL
or secret values.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta66-retire-smoke-20260704T1015Z
```

Observed flow:

```text
WSTA63 prepare session -> pass
WSTA64 readiness audit -> pass
WSTA65 status before retire -> READY
WSTA66 retire marker -> pass
WSTA65 status with retire marker -> RETIRED
```

Observed final public summary:

```text
decision=wsta65-persistent-session-status-pass
session_state=RETIRED
ready_for_live=false
reason=operator-retired
recommended_next_action=rerun-wsta63-then-wsta64-if-live-is-needed
state=PUBLIC_OFF
retire_marker_valid=true
live_execution_requested=false
public_url_value_logged=false
secret_values_logged=0
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private lease artifacts and retire markers remain under `workspace/private/`.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta52_persistent_exposure_design \
  tests.test_server_distro_wsta53_persistent_exposure_plan \
  tests.test_server_distro_wsta54_private_lease_artifact \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof \
  tests.test_server_distro_wsta63_persistent_session_controller \
  tests.test_server_distro_wsta64_persistent_session_readiness_audit \
  tests.test_server_distro_wsta65_persistent_session_status \
  tests.test_server_distro_wsta66_persistent_session_retire
```

Result: `Ran 70 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta65_persistent_session_status.py \
  workspace/public/src/scripts/server-distro/run_wsta66_persistent_session_retire.py
```

Result: pass

Fresh WSTA63 + WSTA64 + WSTA65 + WSTA66 private smoke: pass.

## Next

Persistent exposure is now prepared, freshness-audited, lifecycle-visible, and
explicitly retireable while remaining default-off.  Continue only in one of two
directions: an explicit operator-selected WSTA58 live proof with fresh private
confirm tokens, or further default-off operator UX/reporting that still does not
start public exposure.
