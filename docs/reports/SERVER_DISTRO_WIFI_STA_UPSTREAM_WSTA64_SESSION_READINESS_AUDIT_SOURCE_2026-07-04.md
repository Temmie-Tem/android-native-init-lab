# WSTA64 Persistent Session Readiness Audit Source

- Date: 2026-07-04
- Scope: host-only WSTA63 session readiness audit
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta64-persistent-session-readiness-pass`

## Summary

WSTA64 adds the final host-only audit before an operator may choose to run a
WSTA63-generated WSTA58 live template.  WSTA63 proves that a persistent session
was assembled; WSTA64 proves that the assembled session is still safe to consume
now:

- WSTA63 result must be `wsta63-persistent-session-preflight-pass`.
- Initial WSTA54 private lease must still be unexpired.
- Initial lease must have at least a configurable freshness margin remaining.
- Renewal must be a WSTA53 source so WSTA58 will mint the renewal WSTA54 lease
  after the initial WSTA55 live leg.
- WSTA58 preflight must still report renewal refresh readiness.
- The live template must contain only token placeholders, never raw token values.

This does not execute live exposure.  It only emits a readiness result that an
operator can use immediately before deciding whether to run the existing WSTA58
live gate.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta64_persistent_session_readiness_audit.py`
- `tests/test_server_distro_wsta64_persistent_session_readiness_audit.py`

Default execution is fail-closed.  The runner requires a private WSTA63 result:

```text
--wsta63-result-json workspace/private/runs/server-distro/<wsta63-run>/wsta63_result.json
```

It writes a private `wsta64_result.json` and public output contains only redacted
paths, booleans, TTL metadata, and freshness seconds.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta64-readiness-smoke-20260704T1000Z
```

Observed public summary:

```text
decision=wsta64-persistent-session-readiness-pass
gate_decision=ok
wsta63_pass=true
initial_private_lease_unexpired=true
initial_seconds_remaining=298
initial_seconds_remaining_min_met=true
renewal_source_wsta53_valid=true
renewal_lease_minted_after_initial=true
wsta58_preflight_pass=true
wsta58_renewal_refresh_ready=true
live_template_placeholders_only=true
live_execution_requested=false
ready_for_explicit_wsta58_live_gate=true
public_url_value_logged=false
secret_values_logged=0
```

WSTA64 also has explicit stale-session coverage: the same WSTA63 session shape
blocks if the initial private lease is expired or too close to expiry.

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
  tests.test_server_distro_wsta64_persistent_session_readiness_audit
```

Result: `Ran 55 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta64_persistent_session_readiness_audit.py
```

Result: pass

Fresh WSTA63 + WSTA64 private smoke: pass.

## Next

The live WSTA58 command path is now mechanically prepared and freshness-audited,
but still not selected.  Run live persistent exposure only after an explicit
operator decision, fresh private confirm tokens, WSTA64 readiness pass, and the
existing WSTA58 live gates.  Otherwise continue productizing the default-off
workflow without starting public exposure.
