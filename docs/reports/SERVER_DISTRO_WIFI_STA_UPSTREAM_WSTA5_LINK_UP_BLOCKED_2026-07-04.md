# Server-Distro Wi-Fi STA Upstream WSTA5 Link-Up Blocker

- Date: `2026-07-04`
- Decision: `wsta5-live-link-up-blocked`
- Native resident: `A90 Linux init 0.11.140 (v3384-server-distro-hardware-contract)`
- Device ending state: native V3384, `selftest fail=0`
- Private run dir: `workspace/private/runs/server-distro/wsta5-l3-live2-20260703T192633Z`

## Result

The second WSTA5 live attempt ran the current helper and reached a real pre-L3 blocker.  The
fresh private rootfs summary recorded the current helper staged with the L3 gate and TCP probe
fallback present, `userdata` was refreshed, the temporary SSH key was injected, WSTA2 native
materialization passed, and the device switched into the Debian userdata appliance.

The Debian marker ended before DHCP, gateway ARP, DNS, or TCP/443 could run:

```text
wifi_sta_requested=1
wifi_sta_config_present=1
wifi_sta_wlan0_present=1
ncm_recovery_preserved=1
wifi_sta_wpa_supplicant_rc=255
wifi_sta_started=0
wifi_sta_decision=wifi-sta-wpa-start-failed
wifi_sta_secret_values_logged=0
```

The helper in that boot was still the old link-up behavior, so it ignored the return code from
`ip link set wlan0 up` and reported only the later `wpa_supplicant` failure.  Manual diagnostics
showed the real failure was earlier:

```text
Could not set interface wlan0 flags (UP): Invalid argument
nl80211: Could not set interface 'wlan0' UP
wlan0: Failed to initialize driver interface
```

`ip link show` in Debian left `wlan0` down.  Therefore the current blocker is not D-public,
cloudflared, DNS, ARP, or TCP reachability.  It is the handoff state where native materializes
`wlan0`, but Debian cannot bring that interface administratively UP.

## Source Fix

`a90_dpublic_wifi_sta.sh` now treats `ip link set "$IFACE" up` as an explicit gate:

```text
wifi_sta_link_set_up_rc=<rc>
wifi_sta_decision=wifi-sta-link-up-failed
```

This prevents the next run from hiding the link-up error behind a generic
`wifi-sta-wpa-start-failed` marker.  Tests now pin the new marker and decision string.

## Safety Boundary

- No boot image was built or flashed.
- No forbidden partition was written.
- The only destructive device action was the existing `userdata` format/populate path.
- No public tunnel was started; manual mode left tunnel startup disabled.
- No SSID, PSK, BSSID, MAC, private IP, gateway, DHCP lease, public URL, or token is committed.
- After diagnostics, the device was rebooted back to native V3384 and final `selftest` returned
  `fail=0`.

One operational note: the first `switch_root` attempt returned `handoff-display-owner rc=-16`
while native display ownership was still draining; after the auto HUD stopped, the second
bounded attempt succeeded.  That did not affect the Wi-Fi result.

## Validation

```text
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_wifi_sta.sh

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  tests/test_dpublic_smoke_helpers.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_dpublic_smoke_helpers \
  tests.test_prepare_wsta3_sta_rootfs \
  tests.test_server_distro_debian_rootfs_builder \
  tests.test_server_distro_wifi_sta_upstream_plan
```

Result: `27` host-side tests passed.

## Next

Design the next WSTA unit around the link-up boundary, not around L3.  The useful question is:
which native materialization step, interface mode/state, or cleanup action lets Debian execute
`ip link set wlan0 up` successfully after `switch_root`, with USB/NCM recovery preserved and no
native long-lived STA worker crossing the handoff.
