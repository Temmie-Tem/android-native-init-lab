# WSTA229 Cloudflared Egress Allowlist Live Gate

Date: 2026-07-05

## Verdict

PASS.  The attended WSTA226 live gate was executed with the private WSTA226
route artifact and the full acknowledgement/proof stack.  WSTA88, WSTA80, and
WSTA58 all returned live-pass decisions.  The two short public exposure proofs
both returned their public smoke marker, restored the packet filter, cleaned the
D-public runtime, and ended with native selftest still clean.

## Private Evidence

Private WSTA226 live result:

```text
workspace/private/runs/server-distro/wsta229-cloudflared-egress-allowlist-live-20260705T2310KST/wsta226_result.json
```

Private route artifact:

```text
workspace/private/runs/server-distro/wsta227-route-artifact-from-wsta125-v4-20260705T140201Z/cloudflared_egress_route.json
```

WSTA88 delegated live result:

```text
workspace/private/runs/server-distro/wsta229-cloudflared-egress-allowlist-live-20260705T2310KST/wsta88-cloudflared-egress-allowlist/wsta88_operator_workflow.json
```

## Results

Top-level live decisions:

```text
wsta226=wsta226-cloudflared-egress-allowlist-execute-gate-live-pass
wsta88=wsta88-persistent-operator-workflow-live-pass
wsta80=wsta80-persistent-operator-execute-gate-live-pass
wsta58=wsta58-renewal-manual-stop-live-pass
```

The private route artifact was accepted without logging route values:

```text
schema=a90-wsta226-cloudflared-egress-route-v1
state=CLOUDFLARED_EGRESS_ROUTE_DERIVED_PRIVATE
dns4_count=30
tls4_count=2
route_artifact_ready=true
route_values_logged=false
route_values_redacted=true
```

WSTA58 renewal/manual-stop proof returned:

```text
initial_wsta55_pass=true
renewal_wsta55_pass=true
initial_packet_filter_restore_ok=true
renewal_packet_filter_restore_ok=true
manual_stop_cleanup_ok=true
manual_stop_public_state_off=true
wsta48_all_pass=true
wsta48_redaction_ok=true
```

Both short public proof legs returned:

```text
public_smoke_ok=true
packet_filter_restore_ok=true
dpublic_cleanup_ok=true
native_uplink_profile_cleanup_ok=true
chroot_cleanup_ok=true
final_selftest_fail_zero=true
ttl_expiry_stops_public=true
```

Manual stop returned:

```text
manual_stop_requested=true
manual_stop_public_state=PUBLIC_OFF
wifi_cleanup=wifi-cleanup-done
wifi_status=wifi-status-wlan0-present
autoconnect=wifi-autoconnect-disabled
supplicant_process_count=0
```

Post-live native health:

```text
native_init=0.11.158 build=v3402-dpublic-hud-presenter-restart-policy
selftest=pass=12 warn=1 fail=0
```

## Safety

This unit performed the explicitly gated live D-public action: native-owned
Wi-Fi connect/DHCP, short-lived public tunnel exposure, public smoke checks,
legacy-iptables loopback default-drop, cloudflared egress allowlist application,
and packet-filter restore.  It did not perform a boot flash, forbidden partition
write, userdata write, LSM profile load, or switch-root.

The D-public runtime work image was restored from its clean image for both live
legs.  WSTA58 then performed manual stop cleanup and verified public state
returned to `PUBLIC_OFF`.  Final native health stayed at `selftest fail=0`.

No raw DNS/TLS route values, public URL values, tunnel credentials, Wi-Fi
credentials, or confirm tokens are included in this report.

## Next

Cloudflared egress allowlist hardening is now live-proven through the attended
WSTA226 gate.  Fold WSTA229 into the operator status bundle, then continue the
D-public server endgame from status rather than adding more egress gate
scaffolding.
