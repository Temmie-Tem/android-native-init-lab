# Server-Distro Wi-Fi STA Upstream WSTA5 L3 Gate Source

- Date: `2026-07-04`
- Decision: `wsta5-l3-gate-source-done`
- Device action: none
- Flash action: none

## Result

WSTA5 source hardening is in-tree.  The Debian STA helper no longer returns
`wifi-sta-pass` after DHCP and default-route setup alone.  It now treats DHCP/default-route as an
intermediate state and runs a bounded upstream reachability probe before pass:

```text
wifi_sta_l3_attempted=1
wifi_sta_l3_probe=cloudflare-443
wifi_sta_gateway_ping_rc=<rc>
wifi_sta_gateway_arp_state=<state|none>
wifi_sta_gateway_arp_resolved=<0|1>
wifi_sta_dns_probe_rc=<rc>
wifi_sta_tcp443_probe_rc=<rc>
```

The pass condition is now:

```text
dhclient rc == 0
default route dev == wlan0
gateway ARP state is resolved
DNS lookup succeeds
outbound TCP/443 succeeds
```

If any reachability stage fails, the helper records a specific fail-closed decision:

```text
wifi-sta-l3-gateway-unreachable
wifi-sta-l3-dns-failed
wifi-sta-l3-tcp-failed
```

This directly addresses the WSTA4 failure mode where WPA/DHCP/default-route succeeded but gateway
neighbor resolution stayed incomplete and public tunnel setup timed out.

## Source Changes

- `a90_dpublic_wifi_sta.sh` now probes gateway neighbor state, DNS, and outbound TCP/443 before
  `wifi-sta-pass`.
- `build_debian_aarch64_rootfs.py` includes `netcat-openbsd` so the Debian appliance has a
  conventional outbound TCP probe tool.
- `prepare_wsta3_sta_rootfs.py` installs and verifies `netcat-openbsd` as part of the private STA
  rootfs preparation path; existing WSTA3-style rootfs inputs can be upgraded during preparation.
- Tests now pin the new helper markers and package/tool requirements.
- The WSTA plan now states that WSTA3-style pass requires gateway ARP, DNS, and outbound TCP/443,
  not only DHCP/default-route.

## Safety Boundary

- No device command was run for this source unit.
- No boot image was built or flashed.
- No userdata was formatted or staged.
- No Wi-Fi association, DHCP, ping, DNS, TCP, or public tunnel was attempted by this unit.
- No SSID, PSK, BSSID, MAC, private IP, gateway, DHCP lease, public URL, or token is committed.

## Validation

```text
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_wifi_sta.sh \
  workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  tests/test_dpublic_smoke_helpers.py \
  tests/test_server_distro_debian_rootfs_builder.py \
  tests/test_prepare_wsta3_sta_rootfs.py \
  tests/test_server_distro_wifi_sta_upstream_plan.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_dpublic_smoke_helpers \
  tests.test_server_distro_debian_rootfs_builder \
  tests.test_prepare_wsta3_sta_rootfs \
  tests.test_server_distro_wifi_sta_upstream_plan
```

Result: `26` host-side tests passed.

## Next

Run a WSTA5 live check with a freshly prepared private rootfs that includes `netcat-openbsd`.
Expected useful outcomes:

- If gateway ARP is still unresolved, WSTA5 should fail cleanly as
  `wifi-sta-l3-gateway-unreachable`.
- If ARP works but DNS fails, the next target is Debian resolver/DHCP lease handling.
- If DNS works but TCP/443 fails, the next target is route/firewall/upstream reachability.
- Only after `wifi-sta-pass` includes TCP/443 should the D-public tunnel be retried.
