# WSTA65 Persistent Session Lifecycle Status Source

- Date: 2026-07-04
- Scope: host-only WSTA64 session lifecycle status
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta65-persistent-session-status-pass`

## Summary

WSTA65 adds an operator-facing lifecycle status layer for persistent exposure
sessions.  WSTA64 proves readiness at audit time; WSTA65 re-reads the initial
private lease at status time so an old WSTA64 pass cannot remain green after the
lease ages out.

Session states are:

```text
READY     WSTA64 passed and the initial private lease is still fresh.
STALE     WSTA64 passed before, but the initial lease is now too close to expiry.
EXPIRED   WSTA64 passed before, but the initial lease is now expired.
NOT_READY WSTA64 did not pass or required private artifacts are missing.
```

The runner does not execute live exposure.  It reports the recommended next
action: either the operator may run the explicit WSTA58 live gate, or the session
must be regenerated through WSTA63 and WSTA64.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta65_persistent_session_status.py`
- `tests/test_server_distro_wsta65_persistent_session_status.py`

Default execution is fail-closed until a private WSTA64 result is supplied:

```text
--wsta64-result-json workspace/private/runs/server-distro/<wsta64-run>/wsta64_result.json
```

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta65-status-smoke-20260704T1008Z
```

Observed public summary:

```text
decision=wsta65-persistent-session-status-pass
gate_decision=ok
session_state=READY
ready_for_live=true
initial_seconds_remaining=297
recommended_next_action=operator-may-run-explicit-wsta58-live-gate
state=PUBLIC_OFF
live_execution_requested=false
public_url_value_logged=false
secret_values_logged=0
```

Tests also cover status drift after the WSTA64 audit: a formerly ready WSTA64
result is reclassified as `STALE` near expiry and `EXPIRED` at expiry.

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private lease artifacts remain under `workspace/private/`.

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
  tests.test_server_distro_wsta65_persistent_session_status
```

Result: `Ran 63 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta65_persistent_session_status.py
```

Result: pass

Fresh WSTA63 + WSTA64 + WSTA65 private smoke: pass.

## Next

Persistent exposure is now prepared, freshness-audited, and lifecycle-visible,
but live WSTA58 remains unselected.  Continue only in one of two directions:
explicit operator-selected live proof with fresh private confirm tokens, or
default-off lifecycle productization that still does not start public exposure.
