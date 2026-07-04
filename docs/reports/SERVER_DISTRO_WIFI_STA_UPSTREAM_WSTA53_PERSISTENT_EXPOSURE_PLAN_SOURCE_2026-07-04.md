# WSTA53 Persistent Exposure Plan Source

- Date: 2026-07-04
- Scope: host-side persistent lease parser and redacted plan generator
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta53-persistent-exposure-plan-source-pass`

## Summary

WSTA53 implements the first source rung from the WSTA52 persistent exposure design:

- `workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py`

The runner parses a persistent D-public lease request, rejects forbidden public or
secret fields, enforces bounded TTL and private confirm-token source markers, and
emits a redacted plan.  It performs no live action.

Pass decision:

```text
wsta53-persistent-exposure-plan-pass
```

Default behavior is fail-closed.  Without explicit credentialed-Wi-Fi and public-exposure
acknowledgements, the runner returns a blocked decision and keeps all safety flags false.

## Contract

Accepted lease contract:

```text
schema=a90-wsta-persistent-lease-v1
mode=persistent-dpublic-lease
ttl_sec <= 14400
operator_ack_credentialed_wifi=true
operator_ack_public_exposure=true
native_confirm_token_source=private
public_confirm_token_source=private
public_url_storage=workspace/private-only
```

Forbidden fields are rejected at any nested depth:

```text
raw_public_url
ssid
psk
bssid
mac
ip
gateway
dns
confirm_token_value
native_confirm_token
public_confirm_token
```

The generated redacted plan carries the WSTA52 flow:

```text
WSTA45 operator wrapper
WSTA43 orchestrator
WSTA28 reboot/materialization scan-green precondition
WSTA42 native-owned STA uplink + Debian D-public quick Tunnel
WSTA48 redacted aggregate
```

It also keeps `future_live_allowed=false`; WSTA53 only prepares the WSTA54 private
artifact step.

## CLI Smoke

Template printing:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py \
  --print-template
```

Valid redacted plan smoke:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py \
  --run-dir workspace/private/runs/server-distro/wsta53-smoke \
  --ttl-sec 1800 \
  --ack-credentialed-wifi \
  --ack-public-exposure \
  --native-confirm-token-source private \
  --public-confirm-token-source private \
  --print-full-json
```

Result: `decision=wsta53-persistent-exposure-plan-pass`, `future_live_allowed=false`,
`wsta54_private_artifact_ready=true`, and all device/live safety flags remained false.

## Safety

- No device command ran.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke request,
  userdata format/populate, switch-root, or external service action ran.
- The runner does not import or call `subprocess`, native control tools, WSTA42/WSTA43
  live runners, or Cloudflare tunnel start paths.
- No raw public URL, confirm token, SSID, PSK, BSSID, MAC, IP, gateway, DNS value,
  or device serial is committed.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta53_persistent_exposure_plan \
  tests.test_server_distro_wsta52_persistent_exposure_design
```

Result: `Ran 13 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py
git diff --check
```

Result: pass

## Next

Implement WSTA54 host-only private lease artifact generation.  It should consume the
WSTA53 redacted plan, materialize the private lease under `workspace/private/`, and
still perform no device action.
