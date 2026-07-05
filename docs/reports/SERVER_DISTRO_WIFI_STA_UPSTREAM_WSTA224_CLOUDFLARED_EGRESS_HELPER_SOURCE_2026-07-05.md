# WSTA224 Cloudflared Egress Helper Source Support

Date: 2026-07-05

## Verdict

PASS.  WSTA224 implements the first source-support layer required by the WSTA223
live-gate plan: the packet-filter helper now understands cloudflared egress
allowlist operations, and WSTA42 can opt into them behind explicit route/proof
flags.

This is source support only.  No live packet-filter mutation was run.

## Helper Changes

`a90_dpublic_packet_filter.sh` is now helper version `4` and adds:

```text
preflight-cloudflared-egress-allowlist
apply-cloudflared-egress-allowlist
status-cloudflared-egress-allowlist
restore
```

The added rule shape is service-scoped:

```text
entry_chain=OUTPUT
dedicated_chain=A90_CLOUDFLARED_EGRESS
uid_owner=3902
user=a90tunnel
global_output_default=unchanged
terminal_for_uid=REJECT
```

The apply path is fail-closed unless both DNS and TLS route values are supplied
through runtime environment variables.  The helper emits only counts and
redaction markers for those route values.

## WSTA42 Changes

`run_wsta42_native_uplink_dpublic_tunnel.py` now supports:

```text
--enable-cloudflared-egress-allowlist
--force-cloudflared-egress-allowlist-proof
--cloudflared-egress-dns4 <redacted-runtime-value>
--cloudflared-egress-tls4 <redacted-runtime-value>
```

When the egress allowlist is not enabled, the existing WSTA42/WSTA219
default-drop public path is unchanged.

When it is enabled, WSTA42 requires:

```text
--ack-packet-filter-mutation
--force-packet-filter-restore-proof
--force-cloudflared-egress-allowlist-proof
at least one DNS route value
at least one TLS route value
```

The runner then performs the extra helper phases after default-drop apply and
before cloudflared start:

```text
preflight-cloudflared-egress-allowlist
apply-cloudflared-egress-allowlist
status-cloudflared-egress-allowlist
```

Failure decisions added:

```text
wsta42-blocked-cloudflared-egress-allowlist-proof-required
wsta42-blocked-cloudflared-egress-route-required
wsta42-blocked-cloudflared-egress-preflight
wsta42-blocked-cloudflared-egress-apply
wsta42-blocked-cloudflared-egress-status
```

## Safety

WSTA224 changed source and tests only.  It did not perform any device action,
boot flash, native reboot, Wi-Fi connect/association, DHCP, ping, public tunnel,
public smoke, packet-filter mutation, rootfs mutation, userdata write, LSM
profile load, or switch-root.

The new live behavior remains opt-in and explicit-gated; no helper operation
autostarts.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py tests/test_server_distro_wsta42_native_uplink_dpublic_tunnel.py
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_packet_filter.sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest tests/test_server_distro_wsta42_native_uplink_dpublic_tunnel.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest tests/test_server_distro_wsta42_native_uplink_dpublic_tunnel.py tests/test_server_distro_wsta223_cloudflared_egress_allowlist_live_gate_plan.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_server_distro*.py'
```

Results:

```text
WSTA42 focused tests: 22 tests OK
WSTA42/WSTA223 focused tests: 27 tests OK
server-distro regression: 823 tests OK
```

## Next

Propagate the new WSTA42 opt-in flags through the higher operator surfaces
instead of requiring direct WSTA42 invocation.  The next bounded source unit
should update WSTA43/WSTA45/WSTA55/WSTA58/WSTA80/WSTA88 templates and gates so
the attended cloudflared egress allowlist path can be prepared end-to-end before
any live attempt.
