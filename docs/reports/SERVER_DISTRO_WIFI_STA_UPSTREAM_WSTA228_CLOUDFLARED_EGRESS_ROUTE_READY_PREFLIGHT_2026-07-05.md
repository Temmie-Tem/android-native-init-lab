# WSTA228 Cloudflared Egress Route-Ready Preflight

Date: 2026-07-05

## Verdict

PASS.  Existing private WSTA125 runtime evidence was used to produce a private
WSTA227 route observation, convert it into a WSTA226 route artifact, and prove
WSTA226 route-ready preflight through the WSTA88 default-off execute gate.

No live packet-filter mutation was run in this unit.

## Private Evidence

Source runtime evidence:

```text
workspace/private/runs/server-distro/wsta125-native-upstream-cloudflared-runtime-live-v4-20260705T062106KST/wsta125_result.json
workspace/private/runs/server-distro/wsta125-native-upstream-cloudflared-runtime-live-v4-20260705T062106KST/wsta124_cloudflared.strace
```

Private route observation:

```text
workspace/private/runs/server-distro/wsta228-private-route-observation-from-wsta125-v4-20260705T140201Z/cloudflared_egress_route_observation.json
```

Private WSTA226 route artifact:

```text
workspace/private/runs/server-distro/wsta227-route-artifact-from-wsta125-v4-20260705T140201Z/cloudflared_egress_route.json
```

WSTA226 route-ready preflight:

```text
workspace/private/runs/server-distro/wsta226-route-ready-preflight-from-wsta125-v4-20260705T140201Z/wsta226_result.json
```

## Results

Private observation extraction found:

```text
dns4_count=30
tls4_count=2
route_values_logged=false
public_url_value_logged=false
```

WSTA227 returned:

```text
decision=wsta227-cloudflared-egress-route-artifact-source-pass
observation_ready=true
artifact_ready_for_wsta226=true
```

WSTA226 route-ready preflight returned:

```text
decision=wsta226-cloudflared-egress-allowlist-execute-gate-preflight-pass
route_artifact_ready=true
wsta223_plan_ready=true
wsta88_preflight_pass=true
live_execution_requested=false
```

The WSTA226 public route summary records only counts and redaction markers:

```text
schema=a90-wsta226-cloudflared-egress-route-v1
state=CLOUDFLARED_EGRESS_ROUTE_DERIVED_PRIVATE
dns4_count=30
tls4_count=2
route_values_private=true
route_values_logged=false
route_values_redacted=true
```

## Safety

WSTA228 used existing private runtime evidence and host-side parsing.  It did
not perform any device action, boot flash, native reboot, Wi-Fi connect, DHCP,
public tunnel, public smoke, packet-filter mutation, userdata write, LSM profile
load, or switch-root.

No raw DNS/TLS route values, public URL values, tunnel credentials, Wi-Fi
credentials, or tokens are included in this report.

## Next

The WSTA226 live gate now has a private route artifact and a passing default-off
preflight.  The next step is an attended WSTA226 live run with the same artifact,
private confirm tokens, full packet-filter/egress/control-plane/public-off
proof flags, and immediate restore/public-off verification before returning.
