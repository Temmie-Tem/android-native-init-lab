# WSTA225 Cloudflared Egress Operator Propagation

Date: 2026-07-05

## Verdict

PASS.  WSTA225 propagates the WSTA224 cloudflared egress allowlist opt-in
through the higher operator surfaces, so the attended path no longer requires
direct WSTA42 invocation.

This is source support only.  No live packet-filter mutation was run.

## Source Changes

The following runners now accept and forward:

```text
--enable-cloudflared-egress-allowlist
--force-cloudflared-egress-allowlist-proof
--cloudflared-egress-dns4 <redacted-runtime-value>
--cloudflared-egress-tls4 <redacted-runtime-value>
```

Updated surfaces:

```text
WSTA43 orchestrated native-uplink D-public runner
WSTA45 appliance operator wrapper
WSTA55 short-lived public proof runner
WSTA58 renewal/manual-stop proof runner
WSTA80 persistent operator execute gate
WSTA88 one-command persistent operator workflow
```

Each layer stays fail-closed: enabling the egress allowlist requires the explicit
egress proof flag plus at least one DNS route value and one TLS route value.  The
route values are runtime-only; public results record only counts and redaction
markers.

## Operator Chain

Default-off packet generation remains unchanged.  WSTA76/WSTA78 operator packets
still describe the already-proven WSTA58 template without embedding route
values.  WSTA80/WSTA88 append the egress flags only when the explicit live
delegation path is selected.

This preserves the existing WSTA79 packet/status matching path while allowing an
attended operator to run the egress allowlist path through WSTA88 -> WSTA80 ->
WSTA58 -> WSTA55 -> WSTA45 -> WSTA43 -> WSTA42.

## Safety

WSTA225 changed source and tests only.  It did not perform any device action,
boot flash, native reboot, Wi-Fi connect/association, DHCP, ping, public tunnel,
public smoke, packet-filter mutation, rootfs mutation, userdata write, LSM
profile load, or switch-root.

The new path remains opt-in and explicit-gated.  Without
`--enable-cloudflared-egress-allowlist`, the WSTA219 default-drop public path is
unchanged.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py \
  workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py \
  workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py \
  workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py \
  workspace/public/src/scripts/server-distro/run_wsta80_persistent_operator_execute_gate.py \
  workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta43_orchestrated_native_uplink_dpublic \
  tests.test_server_distro_wsta45_appliance_operator \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof \
  tests.test_server_distro_wsta80_persistent_operator_execute_gate \
  tests.test_server_distro_wsta88_persistent_operator_workflow

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_server_distro*.py'
```

Results:

```text
focused WSTA43/WSTA45/WSTA55/WSTA58/WSTA80/WSTA88 tests: 62 tests OK
server-distro regression: 829 tests OK
```

## Next

Prepare an attended WSTA226 dry-run/live gate wrapper for the cloudflared egress
allowlist path.  It should derive DNS/TLS route values at runtime, keep those
values private, run only through the explicit WSTA88/WSTA80 live delegation, and
prove restore/public-off before returning.
