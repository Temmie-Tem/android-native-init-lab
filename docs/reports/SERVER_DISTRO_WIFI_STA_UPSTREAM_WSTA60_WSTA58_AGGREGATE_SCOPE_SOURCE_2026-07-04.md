# WSTA60 WSTA58 Aggregate Scope Source

- Date: 2026-07-04
- Scope: WSTA58 aggregate input fix after renewal/manual-stop live evidence
- Device action: none for the fix; host-only reaggregate of existing private live evidence
- Flash: none
- Public exposure: none for the fix
- Decision: `wsta60-wsta58-aggregate-scope-source-pass`

## Summary

The WSTA58 renewal refresh retry produced the intended live behavior:

```text
initial_decision=wsta55-short-lived-public-proof-live-pass
renewal_decision=wsta55-short-lived-public-proof-live-pass
manual_stop_cleanup_ok=true
manual_stop_public_state_off=true
redaction_guard_ok=true
public_url_value_logged=false
secret_values_logged=0
```

The top-level WSTA58 runner still returned `wsta58-blocked-wsta48-redaction`
because its WSTA48 aggregate inputs were too broad.  It passed each whole WSTA55
run directory to WSTA48, which recursively included each WSTA55 run's own
`wsta48_result.json`.  Those internal aggregate files intentionally have no
`decision` field, so WSTA48 counted two `missing` decisions and set
`all_pass=false`.

This was a host-side aggregation scope bug, not a public exposure or cleanup
failure.

## Source Change

Updated:

- `workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py`
- `tests/test_server_distro_wsta58_renewal_manual_stop_proof.py`

WSTA58 now aggregates only the two WSTA45 publish roots:

```text
initial-wsta55/wsta45-short-lived-publish
renewal-wsta55/wsta45-short-lived-publish
```

WSTA58 separately checks each WSTA55 top-level decision, so WSTA48 no longer needs
to recurse over WSTA55's internal aggregate artifacts.

## Host-Only Reaggregate Evidence

Private evidence directory:

```text
workspace/private/runs/server-distro/wsta58-live-renewal-refresh-retry-20260704T0936Z
```

Corrected aggregate path:

```text
workspace/private/runs/server-distro/wsta58-live-renewal-refresh-retry-20260704T0936Z/wsta58/wsta60_corrected_wsta48_result.json
```

Corrected aggregate summary:

```text
all_pass=true
result_count=10
wsta27-materialization-scan-gate-pass=2
wsta28-reboot-materialization-scan-gate-pass=2
wsta42-native-uplink-dpublic-tunnel-pass=2
wsta43-orchestrated-native-uplink-dpublic-pass=2
wsta45-appliance-operator-wsta43-profile-pass=2
redaction_guard.ok=true
public_url_value_logged=false
secret_values_logged=0
```

The device was checked after the live attempt:

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
- This fix and reaggregate were host-only.
- The committed report and source changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw live artifacts remain private-only under `workspace/private/`.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof
```

Result: `Ran 10 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py
```

Result: pass

Host-only corrected WSTA48 aggregate over existing private WSTA58 live evidence:
pass.

## Next

Do not immediately loop a third WSTA58 live retry just to turn the top-level
decision green; the last live run already proved both WSTA55 legs and manual stop,
and the remaining issue was source-side aggregation.  If a pristine one-shot
WSTA58 pass is required later, use the fixed runner and the renewal WSTA53 source
mode.
