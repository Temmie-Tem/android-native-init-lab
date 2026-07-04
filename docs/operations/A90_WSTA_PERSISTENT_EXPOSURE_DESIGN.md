# A90 WSTA Persistent Exposure Design

This is the design contract for a future WSTA persistent D-public exposure mode.
It does not authorize a live public run by itself, and it does not replace the
bounded WSTA45 operator publish runbook.  Default state is always public-off.

## Existing Proven Flow

The design builds on the already proven bounded path:

```text
WSTA45 operator wrapper
  -> WSTA43 orchestrator
  -> WSTA28 reboot/materialization scan-green precondition
  -> WSTA42 native-owned STA uplink + Debian D-public quick Tunnel
  -> WSTA48 redacted aggregate
```

Native init remains the Wi-Fi owner.  Debian remains a service surface for the
loopback D-public application and tunnel process.  Public exposure stays outbound
tunnel only; no inbound device port is opened.

## Persistent Does Not Mean Always-On

Persistent mode means a supervised, renewable public lease, not indefinite public
exposure.  A valid lease has a start time, max TTL, operator identity marker, redacted
profile label, and cleanup policy.  When the lease expires or a health gate fails,
the system must stop public exposure and return to public-off.

Lease policy:

```text
default_state=public-off
default_lease_ttl_sec=1800
maximum_lease_ttl_sec=14400
renewal_requires_host_gate=true
boot_autostart_without_valid_private_lease=false
raw_public_url_committed=false
```

## State Machine

```text
PUBLIC_OFF
  -> ARMED_PRIVATE_LEASE
  -> PREFLIGHT_GREEN
  -> PUBLIC_RUNNING
  -> RENEWAL_PENDING
  -> DRAINING
  -> PUBLIC_OFF
```

Incident paths:

```text
PUBLIC_RUNNING -> INCIDENT_STOP -> PUBLIC_OFF
PREFLIGHT_GREEN -> INCIDENT_STOP -> PUBLIC_OFF
ARMED_PRIVATE_LEASE -> INCIDENT_STOP -> PUBLIC_OFF
```

`INCIDENT_STOP` is entered on selftest regression, Wi-Fi status regression,
lost native control channel, failed public smoke, missing cleanup marker, process
duplication, or redaction guard failure.

## Required Gates

Host-side gate before any persistent lease start:

```text
bridge_status_ok=true
resident_version_allowed=true
selftest_fail_zero=true
wsta45_preflight_pass=true
wsta28_scan_green_recent=true
credentialed_wifi_ack=true
public_exposure_ack=true
native_confirm_token_private=true
public_confirm_token_private=true
lease_ttl_within_cap=true
private_run_dir_required=true
```

Device/service gate before the tunnel process starts:

```text
native_owned_wifi_confirmed=true
default_route_is_wlan=true
resolver_ready=true
loopback_smoke_ready=true
single_tunnel_process=true
autoconnect_profile_confirmed=true
secret_values_logged=0
public_url_value_logged=false
```

Stop/cleanup gate before success:

```text
dpublic_cleanup_ok=true
cloudflared_absent=true
smoke_service_absent=true
native_uplink_profile_cleanup_ok=true
helper_cleanup_ok=true
chroot_cleanup_ok=true
wifi_cleanup_ok=true
post_selftest_fail_zero=true
wsta48_redaction_guard_ok=true
```

## Private Lease File

The host may stage a private lease file in the run directory and, for a future live
implementation, copy a redacted lease marker into the Debian service surface.  The
lease file must never be committed.

Required lease fields:

```text
schema=a90-wsta-persistent-lease-v1
mode=persistent-dpublic-lease
ttl_sec=<bounded-integer>
operator_ack_credentialed_wifi=true
operator_ack_public_exposure=true
native_confirm_token_source=private
public_confirm_token_source=private
public_url_storage=workspace/private-only
```

Forbidden lease fields in public artifacts:

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
```

## Supervision Contract

The future service runner must supervise both the loopback application and the tunnel
process.  It must maintain pidfiles under a volatile runtime directory, poll health,
and kill both processes on expiry or failure.  It must be idempotent: repeated stop
commands must leave no tunnel process and no loopback smoke process.

Required supervision behavior:

```text
start_if_no_existing_tunnel=true
duplicate_tunnel_is_failure=true
ttl_expiry_stops_public=true
health_failure_stops_public=true
manual_stop_stops_public=true
cleanup_idempotent=true
status_redacts_url=true
hud_shows_redacted_state_only=true
```

The native menu may display redacted state such as `PUBLIC_OFF`, `LEASE_ACTIVE`, and
`EXPIRES_SOON`, but it must not show or persist the public URL, credentials, raw Wi-Fi
identifiers, or confirm-token values.

## Implementation Rungs

WSTA52 is design only.  The implementation should move in bounded rungs:

```text
WSTA53 source: persistent lease parser and redacted plan generator, no live action
WSTA54 host-only: fail-closed preflight and private lease artifact generation
WSTA55 live: short lease start, public smoke, forced TTL expiry, cleanup proof
WSTA56 live: renewal and manual stop proof
WSTA57 native HUD: redacted persistent state screen, no secret/public URL display
```

No rung may skip the explicit credentialed Wi-Fi acknowledgement, public exposure
acknowledgement, private confirm-token source, cleanup proof, and WSTA48 redacted
aggregation.

## Non-Goals

- No boot flash is part of the persistent exposure start path.
- No raw partition write is part of the persistent exposure path.
- No automatic public exposure starts from a committed config file.
- No public URL, token, SSID, PSK, BSSID, MAC, IP, gateway, or DNS value is committed.
- No weakening of WSTA42/WSTA43/WSTA45 live gates is allowed.
