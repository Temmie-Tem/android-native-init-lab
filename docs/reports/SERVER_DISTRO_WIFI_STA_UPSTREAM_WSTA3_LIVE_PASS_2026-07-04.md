# Server-Distro Wi-Fi STA Upstream WSTA3 Live Pass

- Date: `2026-07-04`
- Decision: `wsta3-debian-sta-live-pass`
- Native resident used for handoff: `A90 Linux init 0.11.140 (v3384-server-distro-hardware-contract)`
- Device ending state: Debian userdata appliance, SSH reachable over USB/NCM admin path, Wi-Fi STA associated, DHCP lease active, default route on `wlan0`
- Private run dir: `workspace/private/runs/server-distro/wsta3-live-20260703T180553Z`

## Result

WSTA3 passed live.  The device booted from the V3384 native handoff image, native materialized
`wlan0`, then `switch_root` handed control to the Debian userdata appliance.  Debian firstboot ran
the opt-in STA helper using private credentials, completed association and DHCP, moved the default
route to `wlan0`, and preserved the USB/NCM host route for recovery/admin access.

Final pass markers:

```text
wifi_sta_requested=1
wifi_sta_wlan0_present=1
wifi_sta_wpa_supplicant_rc=0
wifi_sta_started=1
wifi_sta_carrier_up=1
wifi_sta_dhcp_attempted=1
wifi_sta_dhcp_rc=0
wifi_sta_default_route_router_present=1
wifi_sta_default_route_set_rc=0
wifi_sta_default_route_iface=wlan0
ncm_recovery_preserved_after_dhcp=1
wifi_sta_decision=wifi-sta-pass
wifi_sta_secret_values_logged=0
```

Runtime state check showed `wlan0` up with a dynamic IPv4 lease, default route via `wlan0`,
the USB/NCM host route still present, and `wpa_supplicant` plus `dhclient` running.  Raw SSID,
PSK, MAC/BSSID, IP addresses, gateway, token values, and secret-derived tarball SHA are intentionally
not recorded in this public report.

## Fixes Made During The Live Unit

The first private WSTA3 rootfs was not sufficient for an autonomous Debian STA boot.  The live run
closed these gaps:

- `prepare_wsta3_sta_rootfs.py` now installs the D-public firstboot profile into
  `/etc/a90-d3-firstboot`, so proof-only D3 autoreboot is replaced by the no-autoreboot D-public
  profile and the STA helper is invoked when `/etc/a90-dpublic/wifi-sta-enable` exists.
- The preparer now fail-closes or host-installs the required Debian STA tools:
  `wpasupplicant`, `isc-dhcp-client`, and `iproute2` presence.
- The preparer restores usrmerge links after package extraction, keeping `/bin`, `/sbin`, and
  `/lib` as symlinks into `/usr/*`.  This avoids the observed `switch_root` failure where
  `/sbin/init` existed but its loader path was missing.
- `a90_dpublic_wifi_sta.sh` now reads the DHCP lease router after a successful `dhclient` run and
  explicitly replaces the default route via `wlan0`.  The previous helper associated and got DHCP
  but left default route on `ncm0`.

## Live Sequence

1. Staged the private WSTA3 tarball to the SD runtime path with SHA checked internally and redacted
   publicly.
2. Formatted `userdata` as journaled ext4 through the existing V3384 D4 command surface.
3. Populated `userdata` with the WSTA3 Debian rootfs and injected the existing private-run SSH public
   key for local validation.
4. Switched into Debian and observed failures until rootfs/tool/helper gaps were fixed.
5. Rebooted back to native, ran the WSTA2 no-flash materialization gate, then switched into the
   patched Debian rootfs.
6. Collected final redacted STA markers and network state.

Important operational finding: after a full native reboot, WSTA3 currently depends on running the
WSTA2 native materialization gate before `switch_root`; otherwise Debian firstboot can see
`wifi_sta_wlan0_present=0`.  The accepted final sequence includes that pre-handoff materialization.

## Safety Boundary

- No boot flash was performed in this WSTA3 unit; V3384 was already resident.
- No forbidden partition was written.
- `userdata` was intentionally formatted/refreshed under the D4/WSTA authorization.
- No public tunnel was started.
- No external ping was used for the pass criterion.
- No raw SSID/PSK, raw supplicant config, secret-derived tarball SHA, raw MAC/BSSID, IP address,
  public URL, or token is committed.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_prepare_wsta3_sta_rootfs.py \
  tests/test_dpublic_smoke_helpers.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta2_native_materialization.py --probe-iftype
```

Result: source tests passed, WSTA2 no-flash materialization passed immediately before final
handoff, and final WSTA3 Debian firstboot returned `wifi-sta-pass`.

## Next

Promote this as the STA precondition for D-public tunnel work: before public exposure, boot native,
run WSTA2 materialization, switch into the WSTA3 userdata appliance, confirm `wifi-sta-pass`, then
start the Debian-owned tunnel path.
