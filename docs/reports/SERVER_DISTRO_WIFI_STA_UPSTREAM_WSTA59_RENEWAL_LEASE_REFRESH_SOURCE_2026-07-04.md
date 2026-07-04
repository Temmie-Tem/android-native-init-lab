# WSTA59 Renewal Lease Refresh Source

- Date: 2026-07-04
- Scope: WSTA58 renewal lease timing fix after first live block
- Device action: one bounded WSTA58 live attempt blocked safely after initial WSTA55 pass
- Flash: none
- Public exposure: initial short-lived WSTA55 proof only, cleaned before completion
- Decision: `wsta59-renewal-lease-refresh-source-pass`

## Summary

The first WSTA58 live attempt proved the initial WSTA55 leg, then blocked safely
before the renewal publish:

```text
wsta58_decision=wsta58-blocked-renewal-wsta55
initial_decision=wsta55-short-lived-public-proof-live-pass
renewal_decision=wsta55-blocked-lease-already-expired
manual_stop_cleanup_ok=true
manual_stop_public_state_off=true
wsta48_redaction_ok=true
public_url_value_logged=false
secret_values_logged=0
```

Root cause: WSTA58 minted both private 300-second lease artifacts before starting
the first WSTA55 live proof.  The initial proof can consume the renewal lease's
wall-clock TTL before the second WSTA55 validator runs.

## Source Change

Updated:

- `workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py`
- `tests/test_server_distro_wsta58_renewal_manual_stop_proof.py`

WSTA58 now accepts a renewal source:

```text
--renewal-wsta53-result-json workspace/private/.../wsta53_result.json
```

In that mode, WSTA58 validates the renewal WSTA53 source during preflight but does
not mint the renewal WSTA54 lease until after the initial WSTA55 leg returns.  The
second WSTA55 run therefore receives a fresh private short lease instead of a
pre-aged artifact.

The older `--renewal-lease-artifact-json` path remains for host-only artifact-pair
preflight, but the live retry should use the renewal WSTA53 source path.

## Preflight Evidence

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta58-refresh-preflight-smoke-20260704T0930Z
```

Observed summary:

```text
wsta58_decision=wsta58-renewal-manual-stop-preflight-pass
gate_decision=ok
renewal_lease_refresh_ready=true
distinct_lease_ids_deferred_to_live_refresh=true
public_url_value_logged=false
secret_values_logged=0
```

## Final Health After Block

After the blocked live attempt, independent cleanup/health was checked:

```text
selftest: pass=12 warn=1 fail=0
wifi.autoconnect.decision=wifi-autoconnect-disabled
supplicant.process_count=0
default_route_present=0
ipv4=none
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- The live attempt stopped after the initial WSTA55 proof and before a renewal
  public tunnel attempt.
- Manual stop cleanup returned `PUBLIC_OFF`.
- The committed report and source changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw live artifacts remain private-only under `workspace/private/`.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta53_persistent_exposure_plan \
  tests.test_server_distro_wsta54_private_lease_artifact \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof \
  tests.test_server_distro_wsta48_redacted_result_aggregate
```

Result: `Ran 40 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py \
  workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py \
  workspace/public/src/scripts/server-distro/run_wsta54_private_lease_artifact.py \
  workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py
```

Result: pass

`git diff --check`: pass

## Next

Retry WSTA58 live with an initial WSTA54 private lease and a renewal WSTA53 source,
not a pre-minted renewal lease artifact.  Stop on any repeated renewal failure.
