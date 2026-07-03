# Server-Distro Wi-Fi STA Upstream WSTA4 D-Public STA Blocked

- Date: `2026-07-04`
- Decision: `wsta4-dpublic-sta-upstream-blocked`
- Native resident used for handoff: `A90 Linux init 0.11.140 (v3384-server-distro-hardware-contract)`
- Device ending state: native V3384, USB/NCM admin path reachable, `selftest fail=0`
- Private run dir: `workspace/private/runs/server-distro/wsta4-dpublic-sta-tunnel-20260703T184034Z`

## Result

WSTA4 did not pass.  The D-public loopback service works and the Debian STA helper still reaches
the WSTA3-level pass markers, but a public tunnel over Wi-Fi STA cannot be proven because actual
STA upstream L3 is blocked below cloudflared.

The clean handoff path was reproduced without a boot flash:

1. Rebooted the Debian appliance back to native V3384.
2. Re-ran the WSTA2 native materialization gate; it returned `wsta2-native-materialization-pass`.
3. Switched into the existing WSTA3 userdata appliance.
4. Observed Debian firstboot return the WSTA3 markers: `wifi_sta_dhcp_rc=0`,
   `wifi_sta_default_route_router_present=1`, `wifi_sta_default_route_set_rc=0`,
   `wifi_sta_default_route_iface=wlan0`, `ncm_recovery_preserved_after_dhcp=1`, and
   `wifi_sta_decision=wifi-sta-pass`.
5. Confirmed local D-public smoke over loopback returned `A90_DPUBLIC_SMOKE_OK`.

That proves the appliance and local HTTP side are alive, but it is not enough to prove public
exposure.

## Blocker

The blocking evidence is STA L3/ARP, not the D-public smoke helper:

```text
wpa_state=COMPLETED
wifi_sta_dhcp_rc=0
wifi_sta_default_route_iface=wlan0
ping_gw_rc=1
ping_cf_rc=1
getent_rc=2
tcp443_rc=1
arp gateway state=INCOMPLETE
```

After the device clock was manually corrected, `cloudflared` still failed to request a quick tunnel
with a bounded HTTP timeout.  The route pointed at `wlan0`, but a direct gateway ping failed, DNS
resolution failed, TCP 443 reported no route to host, and neighbor resolution for the STA gateway
remained incomplete.  Host-side LAN probing also could not ARP the device's STA address.

Native-side Wi-Fi corroborated the problem: after returning to native V3384, `wifi config status`
proved the private profile was present and redacted, but `wifi connect-event` timed out with no
CONNECT event, `carrier_up=0`, and `rc=-107`.  So the next unit should treat this as a Wi-Fi client
L2/L3 regression or missing runtime setup, not as a cloudflared-only issue.

## Source Hardening

This unit also hardened the D-public firstboot marker for future runs.  When quick Tunnel mode is
enabled, firstboot now observes the forked `cloudflared` process and records bounded readiness:

```text
tunnel_process_alive=<0|1>
tunnel_url_observed=<0|1>
tunnel_decision=quick-url-ready|quick-url-pending|quick-process-exited
```

The public URL, when observed, is written only to a root-readable runtime sidecar under `/run` and
is not appended to `/run/a90-d3-marker`.  Manual tunnel mode records `tunnel_decision=manual` and
does not report a false quick-start state.

## Safety Boundary

- No boot flash was performed in this WSTA4 unit; V3384 was already resident.
- No forbidden partition was written.
- The run used the existing WSTA3 userdata appliance and existing private STA credentials.
- No raw SSID, PSK, MAC/BSSID, IP address, gateway, public URL, or token is committed.
- The stale public URL probe returned a redacted HTTP 404 and is not treated as exposure success.
- Final device state was native V3384 with `selftest fail=0`.

## Validation

```text
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_wifi_sta.sh

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  tests/test_dpublic_smoke_helpers.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_dpublic_smoke_helpers \
  tests.test_prepare_wsta3_sta_rootfs \
  tests.test_server_distro_wifi_sta_upstream_plan
```

Result: `23` host-side tests passed, and final native `selftest` returned `fail=0`.

## Next

WSTA5 should root-cause STA L3/ARP before attempting public exposure again:

- Add a true L3 gate to the Debian STA helper so WSTA cannot overstate pass after DHCP only.
- Compare the V2237/V2312 Wi-Fi-proven lineage against V3384 native client behavior.
- Determine whether WSTA needs additional native materialization/runtime setup before Debian owns
  `wlan0`.
- Keep cloudflared clock handling fail-closed until STA L3 is proven.
