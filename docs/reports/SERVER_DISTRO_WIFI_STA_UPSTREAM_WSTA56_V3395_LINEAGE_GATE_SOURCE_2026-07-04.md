# WSTA56 V3395 Lineage Gate Source

- Date: 2026-07-04
- Scope: host-side supported-native lineage gate update after WSTA55 live block
- Device action: bounded live attempt already stopped before public tunnel
- Flash: none
- Public exposure: none
- Decision: `wsta56-v3395-lineage-gate-source-pass`

## Summary

The first WSTA55 live short-lease attempt created a fresh 300 second WSTA53/WSTA54
artifact, entered the explicit WSTA55 live gate, and delegated into WSTA45/WSTA43.
It stopped safely before WSTA42/public tunnel work:

```text
wsta55_decision=wsta55-blocked-wsta45-publish
wsta45_decision=wsta45-blocked-wsta43-profile-publish
wsta43_decision=wsta43-blocked-reboot-materialization
wsta28_decision=wsta28-blocked-post-reboot-health
wsta27_after_reboot_decision=wsta27-blocked-v3387-not-resident
```

Root cause: the host-side supported-native lineage list accepted V3387 through V3394,
but WSTA51 moved the resident to V3395 (`v3395-wsta-screenapp-live`).  The WSTA28
post-reboot health summary therefore recorded `contains_supported_native=false` even
though the device booted cleanly as V3395.

## Source Change

Updated:

- `workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py`
- `tests/test_server_distro_wsta24_native_wifi_uplink_client.py`
- `tests/test_server_distro_wsta26_scan_failure_diagnostic.py`

The shared lineage gate now includes:

```text
version=0.11.151
build=v3395-wsta-screenapp-live
```

The function name remains `native_is_v3387` for compatibility with existing WSTA24
through WSTA42 callers, but the accepted set is explicitly the supported native Wi-Fi
uplink lineage, now V3387 through V3395.

## Live Attempt Evidence

Private run directory:

```text
workspace/private/runs/server-distro/wsta55-live-short-lease-20260704T084341Z
```

Relevant redacted observations:

```text
wsta53_decision=wsta53-persistent-exposure-plan-pass
wsta54_decision=wsta54-private-lease-artifact-pass
wsta55_gate_decision=ok
wsta55_public_smoke_ok=false
wsta55_ttl_expiry_stops_public=false
wsta48_redaction_guard_ok=true
```

The attempt stopped at reboot/materialization health before WSTA42, so no public
tunnel URL was obtained and no public smoke request ran.

Post-attempt device health was checked independently:

```text
resident=A90 Linux init 0.11.151 (v3395-wsta-screenapp-live)
selftest: pass=12 warn=1 fail=0
public_exposure=false
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- The attempted live path performed a native reboot but stopped before WSTA42 tunnel
  startup, public URL fetch, or public smoke.
- No raw public URL, confirm-token value, Wi-Fi credential, network address, routing
  value, lease id value, or device serial is committed.
- Private raw evidence remains under `workspace/private/`.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta24_native_wifi_uplink_client \
  tests.test_server_distro_wsta26_scan_failure_diagnostic \
  tests.test_server_distro_wsta27_materialization_preflight \
  tests.test_server_distro_wsta28_reboot_materialization_gate \
  tests.test_server_distro_wsta55_short_lived_public_proof
```

Result: `Ran 30 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py \
  workspace/public/src/scripts/server-distro/run_wsta26_scan_failure_diagnostic.py \
  workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py \
  workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py \
  workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py
```

Result: pass

## Next

Retry WSTA55 live with a fresh short-lived WSTA54 artifact.  The next attempt should
allow WSTA28/WSTA27 to proceed past the V3395 lineage gate and exercise the bounded
materialization scan before any WSTA42 public tunnel work.
