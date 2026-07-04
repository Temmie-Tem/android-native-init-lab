# WSTA63 Persistent Session Controller Source

- Date: 2026-07-04
- Scope: host-only persistent exposure session controller
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta63-persistent-session-preflight-pass`

## Summary

WSTA63 adds the host-side controller that prepares the next WSTA58 persistent
exposure session without running live exposure.  It standardizes the bundle that
was previously assembled manually:

```text
initial WSTA53 short plan
  -> initial WSTA54 private lease artifact
  -> renewal WSTA53 source
  -> WSTA58 host-only preflight
  -> redacted WSTA58 live command template
```

The renewal lease is intentionally not pre-minted.  WSTA63 passes the renewal
WSTA53 source to WSTA58 so the renewal WSTA54 lease is minted only after the
initial WSTA55 live leg returns, preserving the WSTA59 freshness fix.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta63_persistent_session_controller.py`
- `tests/test_server_distro_wsta63_persistent_session_controller.py`

The runner is fail-closed by default.  A host-only preflight session requires:

```text
--prepare-session
--ttl-sec <= 300
--ack-credentialed-wifi
--ack-public-exposure
--native-confirm-token-source private
--public-confirm-token-source private
```

Even with all host-only gates present, WSTA63 does not execute WSTA58 live.  It
prints a command template containing `<native-confirm-token>` and
`<public-confirm-token>` placeholders for the future explicit live gate.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta63-preflight-smoke-20260704T0951Z
```

Observed public summary:

```text
decision=wsta63-persistent-session-preflight-pass
gate_decision=ok
initial_wsta53_pass=true
initial_wsta54_pass=true
initial_private_lease_present=true
renewal_source_wsta53_pass=true
renewal_lease_minted_after_initial=true
wsta58_preflight_pass=true
live_execution_requested=false
public_url_value_logged=false
secret_values_logged=0
```

Generated private files:

```text
initial-wsta53/wsta53_result.json
initial-wsta54/wsta54_private_lease.json
renewal-source-wsta53/wsta53_result.json
wsta58-preflight/wsta58_result.json
wsta63_result.json
wsta63_session_manifest.json
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
  tests.test_server_distro_wsta63_persistent_session_controller
```

Result: `Ran 47 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta63_persistent_session_controller.py
```

Result: pass

Private WSTA63 preflight smoke: pass.

## Next

The next live step is now mechanically prepared but still explicit-gated: use the
WSTA63 session manifest's redacted WSTA58 command template only when the operator
selects a live persistent exposure proof, supplies private confirm tokens, and
accepts the credentialed-Wi-Fi/public-exposure gates.  Keep public exposure
default-off and stop on any WSTA55, cleanup, WSTA48 redaction, or health failure.
