# WSTA58 Renewal Manual-Stop Source

- Date: 2026-07-04
- Scope: source/preflight runner for renewal and manual-stop proof
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta58-renewal-manual-stop-preflight-pass`

## Summary

WSTA58 implements the next persistent-exposure proof rung after the WSTA57 live
short-lease pass.  It proves the host-side contract for renewal/manual stop
without making public exposure always-on:

- renewal requires a second distinct private short lease;
- live execution remains behind an explicit WSTA58 gate;
- the live path delegates to two independent WSTA55 short-lease live proofs;
- after the renewal proof, a final manual public-off cleanup is required;
- WSTA48 redaction remains mandatory before a live pass.

This source unit did not run the live double-publish path.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py`
- `tests/test_server_distro_wsta58_renewal_manual_stop_proof.py`

Default execution is fail-closed.  The runner requires both:

```text
--initial-lease-artifact-json workspace/private/.../wsta54_private_lease.json
--renewal-lease-artifact-json workspace/private/.../wsta54_private_lease.json
```

It reuses WSTA55's private short-lease validator, rejects non-private or expired
artifacts, enforces distinct private lease ids internally, and redacts the actual
lease ids from public output.

The live path is present but gated by:

```text
--execute-renewal-manual-stop
--allow-operator-live
--allow-native-reboot
--allow-public-live
--ack-credentialed-wifi
--ack-public-exposure
--force-ttl-expiry-proof
--force-manual-stop-proof
--native-confirm-token <private>
--public-confirm-token <private>
```

Only then does WSTA58 call WSTA55 twice and require final manual-stop cleanup plus
WSTA48 redaction.

## Preflight Evidence

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta58-preflight-smoke-20260704T0902Z
```

Observed preflight summary:

```text
wsta58_decision=wsta58-renewal-manual-stop-preflight-pass
gate_decision=ok
distinct_lease_ids=true
live_ready=true
public_url_value_logged=false
secret_values_logged=0
```

No device command, native reboot, Wi-Fi association, DHCP, public tunnel, public
smoke, userdata action, switch-root, or external service action ran.

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- Live D-public exposure was not run in this source/preflight unit.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- The committed report and source changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private lease artifacts remain under `workspace/private/`.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof
```

Result: `Ran 8 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py
```

Result: pass

Private WSTA58 preflight smoke: pass.

## Next

Run the WSTA58 live renewal/manual-stop proof only with two fresh `ttl_sec <= 300`
WSTA54 private lease artifacts and the explicit WSTA58 live gate.  Stop on the
first WSTA55 failure, manual-stop cleanup failure, WSTA48 redaction miss, or
post-run health regression.
