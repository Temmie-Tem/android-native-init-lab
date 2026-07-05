# WSTA223 Cloudflared Egress Allowlist Live Gate Plan

Date: 2026-07-05

## Verdict

PASS.  WSTA223 turns the WSTA222 visible operator status into a concrete
attended-live gate plan for the cloudflared egress allowlist.

This is a host-only planning/source-gate unit.  It does not apply packet-filter
rules or start public exposure.

Private evidence:

```text
workspace/private/runs/server-distro/wsta223-cloudflared-egress-allowlist-live-gate-plan-20260705T222716KST/wsta223_result.json
workspace/private/runs/server-distro/wsta223-cloudflared-egress-allowlist-live-gate-plan-20260705T222716KST/wsta223_cloudflared_egress_allowlist_live_gate_plan.json
workspace/private/runs/server-distro/wsta223-cloudflared-egress-allowlist-live-gate-plan-20260705T222716KST/wsta223_cloudflared_egress_allowlist_live_gate_plan.md
```

Decision:

```text
wsta223-cloudflared-egress-allowlist-live-gate-plan-source-pass
```

## Planned State

The emitted plan records:

```text
schema=a90-wsta223-cloudflared-egress-allowlist-live-gate-plan-v1
state=CLOUDFLARED_EGRESS_ALLOWLIST_LIVE_GATE_PLANNED
service=cloudflared-quick-tunnel
hardening_lever=legacy-iptables-cloudflared-egress-allowlist
backend=legacy-iptables
activation=attended-explicit-live-gate-after-default-drop
default_public_off=true
live_execution_requested=false
packet_filter_mutation_by_wsta223=false
blocked_until_source_exists=true
```

The candidate rule shape is service-scoped:

```text
entry_chain=OUTPUT
dedicated_chain=A90_CLOUDFLARED_EGRESS
uid_owner=3902
user=a90tunnel
allow_dns=route-resolved-live-preflight-required
allow_tls=route-resolved-live-preflight-required
global_output_default=unchanged-until-live-proof
terminal_for_uid=REJECT-or-DROP-after-live-preflight
```

## Required Helper Ops

The next source unit must add these packet-filter helper operations before live
execution is allowed:

```text
preflight-cloudflared-egress-allowlist
apply-cloudflared-egress-allowlist
status-cloudflared-egress-allowlist
restore
```

## Required Live Phases

The planned live gate must prove, in order:

```text
preflight
derive-redacted-egress-route
apply-after-default-drop
prove-service-and-nonwidening
restore-and-public-off
```

The plan requires owner-match support for uid `3902`, exact restore snapshots,
redacted DNS/TLS route derivation, loopback default-drop before egress
allowlist, USB/NCM control-plane survival, successful cloudflared public smoke,
no ACCEPT rules for unrelated uid traffic, exact restore, final `PUBLIC_OFF`,
and clean final native health.

## Evidence Folded

WSTA223 accepts the plan only when both inputs agree:

```text
WSTA222 operator status: concrete egress allowlist next actions are present, abstract next-hardening action retired
WSTA221 policy: owner-scoped OUTPUT rule shape, fail-closed route requirements, default-drop preservation, exact restore and control-plane contracts
```

Representative checks:

```text
operator_status_ready=true
wsta221_policy_ready=true
plan_ready=true
```

## Safety

This was host-only plan generation.  No device action, boot flash, native
reboot, Wi-Fi connect/association, DHCP, ping, public tunnel, public smoke,
packet-filter mutation, rootfs mutation, userdata write, LSM profile load, or
switch-root occurred.

Safety fields remained:

```text
device_action=false
boot_flash=false
native_reboot=false
wifi_connect=false
dhcp=false
public_tunnel=false
public_smoke=false
packet_filter_mutation=false
userdata_touch=false
switch_root=false
public_url_value_logged=false
secret_values_logged=0
```

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta223_cloudflared_egress_allowlist_live_gate_plan.py tests/test_server_distro_wsta223_cloudflared_egress_allowlist_live_gate_plan.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest tests/test_server_distro_wsta221_cloudflared_egress_allowlist_policy.py tests/test_server_distro_wsta223_cloudflared_egress_allowlist_live_gate_plan.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_server_distro*.py'
```

Results:

```text
WSTA223 unit tests: 5 tests OK
WSTA221/WSTA223 focused tests: 9 tests OK
server-distro regression: 821 tests OK
host-only WSTA223 run: PASS
```

## Code Changes

- Added `run_wsta223_cloudflared_egress_allowlist_live_gate_plan.py`.
- Added focused WSTA223 tests for valid plan generation, explicit/private
  gates, concrete WSTA222 next-action requirements, WSTA221 no-mutation and
  owner-scope requirements, and plan helper/ack regression checks.

## Next

Implement the WSTA224 source support: extend the packet-filter helper and
runner surfaces so the planned cloudflared egress allowlist gate can be
preflighted and executed only through an attended explicit live path.
