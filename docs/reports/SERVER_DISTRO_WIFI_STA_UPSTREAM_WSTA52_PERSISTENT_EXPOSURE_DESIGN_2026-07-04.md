# WSTA52 Persistent Exposure Design

- Date: 2026-07-04
- Scope: persistent D-public exposure design contract
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta52-persistent-exposure-design-pass`

## Summary

WSTA52 defines the next WSTA rung after the live-proven native menu surface:

- design doc: `docs/operations/A90_WSTA_PERSISTENT_EXPOSURE_DESIGN.md`

The design deliberately does not make public exposure always-on.  It defines a
supervised, renewable public lease with default public-off behavior, bounded TTL,
explicit host gates, cleanup requirements, and redacted status/reporting.

It builds on the proven bounded flow:

```text
WSTA45 operator wrapper
  -> WSTA43 orchestrator
  -> WSTA28 reboot/materialization scan-green precondition
  -> WSTA42 native-owned STA uplink + Debian D-public quick Tunnel
  -> WSTA48 redacted aggregate
```

## Contract

Key policy markers:

```text
default_state=public-off
default_lease_ttl_sec=1800
maximum_lease_ttl_sec=14400
renewal_requires_host_gate=true
boot_autostart_without_valid_private_lease=false
raw_public_url_committed=false
```

Required gate groups:

- host preflight: bridge health, allowed resident, `selftest fail=0`, WSTA45 preflight,
  recent WSTA28 scan-green, credentialed Wi-Fi acknowledgement, public exposure
  acknowledgement, private confirm-token source, bounded TTL, private run directory;
- device/service preflight: native-owned Wi-Fi confirmed, WLAN default route, resolver
  ready, loopback service ready, single tunnel process, redacted logging;
- cleanup before success: D-public cleanup, tunnel absent, smoke service absent, native
  uplink profile cleanup, helper cleanup, chroot cleanup, Wi-Fi cleanup, post selftest,
  WSTA48 redaction guard.

Implementation rungs are fixed as:

```text
WSTA53 source: persistent lease parser and redacted plan generator, no live action
WSTA54 host-only: fail-closed preflight and private lease artifact generation
WSTA55 live: short lease start, public smoke, forced TTL expiry, cleanup proof
WSTA56 live: renewal and manual stop proof
WSTA57 native HUD: redacted persistent state screen, no secret/public URL display
```

## Safety

- No live command ran.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke request,
  userdata format/populate, or switch-root action ran.
- The design states that persistent exposure start does not include boot flash or raw
  partition writes.
- No raw public URL, confirm token, SSID, PSK, BSSID, MAC, IP, gateway, DNS value,
  or device serial is committed.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta52_persistent_exposure_design \
  tests.test_server_distro_wsta49_operator_runbook \
  tests.test_server_distro_wsta45_appliance_operator
```

Result: `Ran 17 tests ... OK`

```text
git diff --check
```

Result: pass

## Next

Implement WSTA53 as source-only: a persistent lease parser and redacted plan
generator that is fail-closed by default and performs no live action.  It should use
the WSTA52 contract as the source of truth and prepare the WSTA54 host-only private
lease artifact step.
