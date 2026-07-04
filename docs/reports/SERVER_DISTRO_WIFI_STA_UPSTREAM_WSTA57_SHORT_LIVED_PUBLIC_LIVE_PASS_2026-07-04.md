# WSTA57 Short-Lived Public Live Pass

- Date: 2026-07-04
- Scope: WSTA55 live short-lived public proof with pre/post reboot public-off cleanup gates
- Device action: bounded WSTA55 live run through WSTA45/WSTA43/WSTA42
- Flash: none
- Public exposure: short-lived quick tunnel only, URL redacted, cleaned before completion
- Decision: `wsta55-short-lived-public-proof-live-pass`

## Summary

WSTA57 closes the first live persistent-lease proof rung.  The run created a fresh
private WSTA53/WSTA54 lease artifact with `ttl_sec <= 300`, entered the explicit
WSTA55 live gate, delegated through the existing WSTA45 -> WSTA43 -> WSTA42 path,
proved public smoke, then verified cleanup and redaction before ending.

Private evidence directory:

```text
workspace/private/runs/server-distro/wsta55-live-short-lease-postclean-20260704T085251Z
```

Run window:

```text
started_utc=20260704T085251Z
ended_utc=20260704T085841Z
```

## Source Changes

Two cleanup gates were added before treating WSTA55 as a live publish runner:

- `run_wsta55_short_lived_public_proof.py` now performs a pre-live public-off
  cleanup before WSTA45.  It hides the native menu, disables Wi-Fi autoconnect,
  runs Wi-Fi cleanup, checks Wi-Fi status, and stops before live publication if
  the cleanup summary is not clean.
- `run_wsta28_reboot_materialization_gate.py` now repeats the public-off cleanup
  after the required native warm reboot and post-reboot health check, before
  nested WSTA27 materialization.  This handles reboot-created menu/autoconnect
  state before any WSTA42 public tunnel work can run.

Both summaries record only allowlisted transport status, decisions, process
counts, and redaction booleans.

## Live Evidence

Top-level WSTA55 result:

```text
decision=wsta55-short-lived-public-proof-live-pass
wsta45_pass=true
public_smoke_ok=true
dpublic_cleanup_ok=true
native_uplink_profile_cleanup_ok=true
chroot_cleanup_ok=true
ttl_expiry_stops_public=true
wsta48_all_pass=true
wsta48_redaction_ok=true
final_selftest_fail_zero=true
public_url_value_logged=false
secret_values_logged=0
```

Nested publish decisions:

```text
wsta45_decision=wsta45-appliance-operator-wsta43-profile-pass
wsta43_decision=wsta43-orchestrated-native-uplink-dpublic-pass
wsta28_decision=wsta28-reboot-materialization-scan-gate-pass
wsta42_decision=wsta42-native-uplink-dpublic-tunnel-pass
```

WSTA42 checks included:

```text
default_route_wlan0=true
resolver_ready=true
local_smoke_ok=true
tunnel_url_observed=true
public_smoke_ok=true
dpublic_cleanup_ok=true
native_uplink_profile_cleanup_ok=true
final_selftest_fail_zero=true
public_url_value_logged=false
secret_values_logged=0
```

WSTA48 redaction aggregate:

```text
all_pass=true
input_count=1
result_count=5
public_url_value_logged=false
secret_values_logged=0
redaction_guard.ok=true
```

## Independent Final Health

After the WSTA55 run finished, the device was checked independently:

```text
resident=A90 Linux init 0.11.151 (v3395-wsta-screenapp-live)
selftest: pass=12 warn=1 fail=0
wifi.autoconnect.decision=wifi-autoconnect-disabled
supplicant.process_count=0
default_route_present=0
ipv4=none
```

This confirms the live proof did not leave the public path or Wi-Fi client
runtime active as a persistent state.

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- Public exposure was bounded to the existing WSTA42 quick-tunnel proof path and
  cleaned before the run completed.
- The committed report and source changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw live artifacts remain private-only under `workspace/private/`.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta28_reboot_materialization_gate \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta24_native_wifi_uplink_client \
  tests.test_server_distro_wsta26_scan_failure_diagnostic
```

Result: `Ran 25 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py \
  workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py
```

Result: pass

`git diff --check`: pass

## Next

Persistent exposure still remains default-off.  The next bounded rung can be the
WSTA52-planned renewal/manual-stop proof, using the WSTA55 cleanup and WSTA48
redaction gates as mandatory preconditions.
