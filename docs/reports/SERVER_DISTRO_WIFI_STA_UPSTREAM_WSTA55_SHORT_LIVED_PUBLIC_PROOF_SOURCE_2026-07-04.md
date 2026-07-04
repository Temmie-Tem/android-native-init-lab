# WSTA55 Short-Lived Public Proof Source

- Date: 2026-07-04
- Scope: source/preflight runner for short-lived persistent public proof
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta55-short-lived-public-proof-source-pass`

## Summary

WSTA55 adds the gated runner for the first live persistent-lease proof:

- `workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py`

Default execution is host-only preflight.  It validates a WSTA54 private lease
artifact and returns live-ready state without touching the device.  Actual public
exposure requires a separate explicit WSTA55 live gate.

The runner delegates live execution to the already proven WSTA45 -> WSTA43 -> WSTA42
path only when every live flag is present.  After a live run, WSTA55 requires WSTA48
redaction, public smoke, cleanup markers, final selftest, and forced TTL-expiry
proof before it can return a live pass.

## Contract

Accepted private artifact:

```text
schema=a90-wsta-private-lease-artifact-v1
state=ARMED_PRIVATE_LEASE
mode=persistent-dpublic-lease
ttl_sec <= 300
wsta55_explicit_live_gate_required=true
wsta54_live_allowed=false
public_url_storage=workspace/private-only
confirm_token_sources={native:private, public:private}
public_url_value_logged=false
secret_values_logged=0
```

Live gate:

```text
--execute-live-short-lease
--allow-operator-live
--allow-native-reboot
--allow-public-live
--ack-credentialed-wifi
--ack-public-exposure
--force-ttl-expiry-proof
--native-confirm-token <private>
--public-confirm-token <private>
```

Live pass requirements:

```text
wsta45_pass=true
wsta48_redaction_ok=true
wsta48_all_pass=true
public_smoke_ok=true
dpublic_cleanup_ok=true
native_uplink_profile_cleanup_ok=true
chroot_cleanup_ok=true
final_selftest_fail_zero=true
ttl_expiry_stops_public=true
```

## CLI Smoke

Private WSTA53/WSTA54 input was generated with a 60 second TTL:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py \
  --run-dir workspace/private/runs/server-distro/wsta55-smoke/wsta53 \
  --ttl-sec 60 \
  --ack-credentialed-wifi \
  --ack-public-exposure \
  --native-confirm-token-source private \
  --public-confirm-token-source private

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta54_private_lease_artifact.py \
  --run-dir workspace/private/runs/server-distro/wsta55-smoke/wsta54 \
  --wsta53-result-json workspace/private/runs/server-distro/wsta55-smoke/wsta53/wsta53_result.json
```

WSTA55 preflight consumed the private artifact:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py \
  --run-dir workspace/private/runs/server-distro/wsta55-smoke/wsta55 \
  --lease-artifact-json workspace/private/runs/server-distro/wsta55-smoke/wsta54/wsta54_private_lease.json
```

Result:

```text
decision=wsta55-short-lived-public-proof-preflight-pass
gate_decision=ok
ttl_sec=60
short_lease_max_ttl_sec=300
lease_id_present=true
lease_id_value_redacted=true
live_execution_requested=false
wsta55_live_ready=true
```

Template printing also passed and emitted placeholders for both confirm tokens.

## Safety

- No device command ran.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke request,
  userdata format/populate, switch-root, or external service action ran.
- The runner rejects non-private run directories and non-private lease artifact paths.
- The runner rejects expired artifacts and artifacts above the short-proof TTL cap.
- The live path still delegates through WSTA45, so WSTA45/WSTA43/WSTA42 gates remain
  load-bearing rather than bypassed.
- No raw public URL, confirm-token value, Wi-Fi credential, network address, routing
  value, lease id value, or device serial is committed.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta54_private_lease_artifact \
  tests.test_server_distro_wsta48_redacted_result_aggregate \
  tests.test_server_distro_wsta45_appliance_operator
```

Result: `Ran 30 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py
git diff --check
```

Result: pass

## Next

The next rung can be the actual WSTA55 live short-lived proof using a fresh private
artifact with `ttl_sec <= 300` and the explicit live gate.  It should stop on any
WSTA45/WSTA43/WSTA42 failure, cleanup miss, WSTA48 redaction miss, or post-run
`selftest` regression.
