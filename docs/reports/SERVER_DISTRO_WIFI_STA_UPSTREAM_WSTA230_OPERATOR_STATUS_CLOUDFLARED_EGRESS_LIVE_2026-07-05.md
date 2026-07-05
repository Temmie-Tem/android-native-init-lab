# WSTA230 Operator Status Cloudflared Egress Live

Date: 2026-07-05
Scope: host-only WSTA108 status folding

## Verdict

PASS.  WSTA230 folds the WSTA229 attended cloudflared egress allowlist live
proof into the WSTA108 operator server status bundle.  The operator status now
treats the cloudflared egress allowlist as live-proven and retires the
egress-live-gate next action.

## Private Evidence

Representative host-only status run:

```text
workspace/private/runs/server-distro/wsta230-operator-status-cloudflared-egress-live-20260705T2332KST/wsta108_operator_server_status.json
workspace/private/runs/server-distro/wsta230-operator-status-cloudflared-egress-live-20260705T2332KST/wsta108_operator_server_status.md
```

Input live proof:

```text
workspace/private/runs/server-distro/wsta229-cloudflared-egress-allowlist-live-20260705T2310KST/wsta226_result.json
```

Decision:

```text
wsta108-operator-server-status-source-pass
```

## Status State

`run_wsta108_operator_server_status.py` now accepts:

```text
--wsta229-cloudflared-egress-allowlist-live-json
```

The supplied JSON must be a private WSTA226 live-pass result.  WSTA108
fail-closes if the proof is non-pass or if any required WSTA226/WSTA88/WSTA80/
WSTA58/WSTA55 restore, smoke, public-off, redaction, or route-summary condition
is missing.

The compact status object is:

```text
server_status.hardening.cloudflared_egress_allowlist_live
```

Pass state:

```text
CLOUDFLARED_EGRESS_ALLOWLIST_ATTENDED_LIVE_PROVEN
```

Accepted status fields include:

```text
cloudflared_egress_allowlist_live_proven=true
dns4_count=30
tls4_count=2
route_values_redacted=true
route_values_logged=false
default_public_off=true
ack_packet_filter_mutation=true
force_packet_filter_restore_proof=true
force_cloudflared_egress_allowlist_proof=true
initial_public_smoke_ok=true
renewal_public_smoke_ok=true
initial_packet_filter_restore_ok=true
renewal_packet_filter_restore_ok=true
manual_stop_cleanup_ok=true
public_state_after_manual_stop=PUBLIC_OFF
wsta48_all_pass=true
wsta48_redaction_ok=true
```

## Operator Actions

With WSTA219 attended default-drop live evidence, WSTA221 policy evidence, and
WSTA229 egress live evidence supplied, WSTA108 now reports:

```text
keep-public-exposure-default-off
use-explicit-wsta88-live-gate-only-when-attended
continue-dpublic-server-endgame-after-cloudflared-egress-live
```

The previous live-gate actions are retired from the current status:

```text
prepare-attended-cloudflared-egress-allowlist-live-gate
move-to-cloudflared-egress-allowlist-live-gate
```

## Safety

WSTA230 is host-only.  It reads existing private run artifacts and emits a
status bundle.

It did not perform any device action, boot flash, native reboot, Wi-Fi connect,
DHCP, public tunnel, public smoke, packet-filter mutation, rootfs mutation,
userdata write, LSM profile load, or switch-root.

No raw DNS/TLS route values, public URL values, tunnel credentials, Wi-Fi
credentials, confirm tokens, or route endpoints are included in this report.

## Validation

Static compile:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py
```

Focused WSTA108/WSTA226 tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_wsta108_operator_server_status tests.test_server_distro_wsta226_cloudflared_egress_allowlist_execute_gate
```

Result: `72 tests OK`.

Full server-distro regression:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_server_distro*.py'
```

Result: `843 tests OK`.

## Next

Continue the D-public server endgame from the WSTA108 status frontier.  The
cloudflared egress allowlist is now policy-defined and attended-live-proven, so
the next unit should focus on the remaining serverization/user-facing service
gap rather than adding more egress gate scaffolding.
