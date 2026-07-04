# WSTA83 WSTA80 Execute Gate To WSTA58 Live

- Date: 2026-07-04
- Scope: explicitly gated WSTA80 delegation into WSTA58 renewal/manual-stop live proof
- Resident: `A90 Linux init 0.11.153 (v3397-wsta-execute-gate-screen)`
- Private run: `workspace/private/runs/server-distro/wsta83-wsta80-wsta58-live-20260704T120533Z/`
- Decision: `wsta80-persistent-operator-execute-gate-live-pass`

## Summary

WSTA83 proves the full default-off operator handoff: a fresh WSTA72-WSTA79
private packet/status pipeline produced a current WSTA80 execute gate, and
WSTA80 then delegated to WSTA58 only after the explicit live flags and confirm
tokens were supplied in-process.

The delegated WSTA58 run passed:

```text
wsta58-renewal-manual-stop-live-pass
initial_wsta55_pass=true
renewal_wsta55_pass=true
manual_stop_cleanup_ok=true
manual_stop_public_state_off=true
wsta48_redaction_ok=true
wsta48_all_pass=true
```

No boot image was flashed.  The run did intentionally perform native warm
reboots, credentialed Wi-Fi association/DHCP through the native-owned uplink
profile, two short-lived public tunnel publishes, two public smoke checks, and
final cleanup back to `PUBLIC_OFF`.

## Fresh Execute Gate

The fresh host-only preparation chain ran in the same private run tree:

```text
wsta72-persistent-prepare-to-arm-pass
wsta73-persistent-arming-packet-pass
wsta75-persistent-arming-inventory-pass
wsta76-persistent-launch-brief-pass
wsta77-persistent-launch-brief-summary-pass
wsta78-persistent-operator-packet-pass
wsta79-persistent-operator-packet-status-pass
wsta80-persistent-operator-execute-gate-preflight-pass
```

The WSTA79 state was `READY_TO_RUN_DEFAULT_OFF`, and the WSTA80 state was
`READY_FOR_EXPLICIT_WSTA58_LIVE_GATE` with `initial_seconds_remaining=299`.
The command template still contained `<native-confirm-token>` and
`<public-confirm-token>` placeholders; raw token values were not written into
the public template or report.

## Live Result

Overall WSTA80 live result:

```text
started_utc=20260704T120533Z
ended_utc=20260704T121710Z
decision=wsta80-persistent-operator-execute-gate-live-pass
wsta58_pass=true
default_public_off=true
explicit_live_gate=true
public_url_value_logged=false
secret_values_logged=0
```

Initial WSTA55 leg:

```text
started_utc=20260704T120533Z
ended_utc=20260704T121120Z
decision=wsta55-short-lived-public-proof-live-pass
wsta45_pass=true
public_smoke_ok=true
dpublic_cleanup_ok=true
native_uplink_profile_cleanup_ok=true
chroot_cleanup_ok=true
final_selftest_fail_zero=true
ttl_expiry_stops_public=true
wsta48_redaction_ok=true
wsta48_all_pass=true
```

Renewal WSTA55 leg:

```text
started_utc=20260704T121120Z
ended_utc=20260704T121709Z
decision=wsta55-short-lived-public-proof-live-pass
wsta45_pass=true
public_smoke_ok=true
dpublic_cleanup_ok=true
native_uplink_profile_cleanup_ok=true
chroot_cleanup_ok=true
final_selftest_fail_zero=true
ttl_expiry_stops_public=true
wsta48_redaction_ok=true
wsta48_all_pass=true
```

Both WSTA42 sub-runs passed the same live surface:

```text
native_uplink_confirmed=true
default_route_wlan0=true
resolver_ready=true
local_smoke_ok=true
tunnel_url_observed=true
public_smoke_ok=true
dpublic_cleanup_ok=true
native_uplink_profile_cleanup_ok=true
chroot_cleanup_ok=true
final_selftest_fail_zero=true
```

## Post-Run Health

After the live proof completed, a separate resident health check still reported:

```text
version: 0.11.153 build=v3397-wsta-execute-gate-screen
status: BOOT OK shell 6.2s
selftest: pass=12 warn=1 fail=0
transport: serial/ncm/tcpctl ready
storage: sd mounted rw
autohud: running
```

## Safety

- No boot flash ran in WSTA83.
- No forbidden partition was touched.
- No userdata format/populate or switch-root ran.
- Public tunnel exposure was short-lived and gated through WSTA80/WSTA58/WSTA55.
- WSTA58 manual-stop cleanup returned the public state to `PUBLIC_OFF`.
- Public URL values, confirm-token values, raw wireless credentials, network
  identifiers, routable addresses, gateway/DNS values, lease IDs, and device
  serials are not committed here.
- Private public URL/body artifacts remain under `workspace/private/` only.

## Observation

Both WSTA42 legs reinstalled the Debian rootfs image before mounting it because
the remote image SHA differed from the clean staged image SHA at the start of
each leg, then matched after install.  This is consistent with the current
read-write chroot workflow mutating the ext4 image between runs.  It did not
break correctness, but it made the live proof much slower than the public
publish itself.  A future optimization should preserve a clean base image or
move mutable runtime state outside the base image before repeating this path.

## Next

The WSTA80 execute gate and WSTA58 renewal/manual-stop live path are now
end-to-end proven on V3397.  The next WSTA work should be either default-off
operator UX around this proven flow, or a targeted performance/cleanliness unit
for the rootfs mutation/reinstall cost observed here.
