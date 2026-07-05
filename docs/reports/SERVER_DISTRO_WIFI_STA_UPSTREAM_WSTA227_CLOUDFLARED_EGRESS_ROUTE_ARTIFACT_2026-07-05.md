# WSTA227 Cloudflared Egress Route Artifact

Date: 2026-07-05

## Verdict

PASS.  WSTA227 adds the private route-artifact builder required by WSTA226.

This is source support only.  No live device action or packet-filter mutation
was run.

## What Changed

New runner:

```text
workspace/public/src/scripts/server-distro/run_wsta227_cloudflared_egress_route_artifact.py
```

The runner consumes a private attended route observation:

```text
schema=a90-wsta227-cloudflared-egress-route-observation-v1
state=CLOUDFLARED_EGRESS_ROUTE_OBSERVED_PRIVATE
source=attended-live-runtime
dns4=[private IPv4/CIDR values]
tls4=[private IPv4/CIDR values]
route_values_private=true
route_values_logged=false
```

It emits the WSTA226-compatible private artifact:

```text
schema=a90-wsta226-cloudflared-egress-route-v1
state=CLOUDFLARED_EGRESS_ROUTE_DERIVED_PRIVATE
dns4=[private IPv4/CIDR values]
tls4=[private IPv4/CIDR values]
route_values_private=true
route_values_logged=false
```

Public output records only DNS/TLS counts, source metadata, path, and redaction
markers.  Raw route values are written only to the private artifact.

## Validation Rules

WSTA227 fail-closes unless:

```text
--emit-route-artifact is supplied
run dir and observation input are under workspace/private
observation schema/state match
source is attended-live-runtime or operator-private-runtime-observation
DNS and TLS route lists are non-empty
targets parse as IPv4 or IPv4/CIDR
resolver, DNS route, and TLS route evidence are true
route_values_private=true
route_values_logged=false
public_url_value_logged=false
secret_values_logged=0
the produced artifact passes WSTA226 validate_route_artifact()
```

## Safety

WSTA227 changed source and tests only.  It did not perform any device action,
boot flash, native reboot, Wi-Fi connect/association, DHCP, ping, public tunnel,
public smoke, packet-filter mutation, rootfs mutation, userdata write, LSM
profile load, or switch-root.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta227_cloudflared_egress_route_artifact.py \
  tests/test_server_distro_wsta227_cloudflared_egress_route_artifact.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta227_cloudflared_egress_route_artifact

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta226_cloudflared_egress_allowlist_execute_gate \
  tests.test_server_distro_wsta227_cloudflared_egress_route_artifact

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_server_distro*.py'
```

Results:

```text
WSTA227 focused tests: 5 tests OK
WSTA226/WSTA227 focused tests: 11 tests OK
server-distro regression: 840 tests OK
```

## Next

Generate a private route observation from attended runtime state, convert it
with WSTA227, then use the resulting private artifact in the WSTA226 live gate.
The live gate must remain operator-supervised and must prove restore/public-off
before returning.
