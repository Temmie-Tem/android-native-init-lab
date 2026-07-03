# Server-Distro Wi-Fi STA Upstream WSTA7 WPA Control Association Pass

- Date: `2026-07-04`
- Decision: `wsta7-wpa-cli-association-l3-live-pass`
- Native resident: `A90 Linux init 0.11.140 (v3384-server-distro-hardware-contract)`
- Device ending state: native V3384, `selftest fail=0`
- Private run dir: `workspace/private/runs/server-distro/wsta7-assoc-live-20260703T194515Z`

## Result

WSTA7 closed the WSTA6 carrier/association blocker.  The Debian STA helper now mirrors the
native-good supplicant control sequence after `wpa_supplicant` starts:

```text
DRIVER COUNTRY KR
SCAN
ENABLE_NETWORK 0
SELECT_NETWORK 0
REASSOCIATE
STATUS
```

The helper records only redacted status markers.  The fresh WSTA7 userdata appliance boot reached
association, DHCP, route ownership, and L3 reachability over `wlan0`:

```text
wifi_sta_link_set_up_rc=0
wifi_sta_wpa_supplicant_rc=0
wifi_sta_started=1
wifi_sta_ctrl_ready=1
wifi_sta_ctrl_driver_country_rc=0
wifi_sta_ctrl_scan_rc=0
wifi_sta_ctrl_enable_network_rc=0
wifi_sta_ctrl_select_network_rc=0
wifi_sta_ctrl_reassociate_rc=0
wifi_sta_ctrl_status_wpa_state=COMPLETED
wifi_sta_ctrl_status_key_mgmt=WPA2-PSK
wifi_sta_ctrl_status_completed=1
wifi_sta_carrier_up=1
wifi_sta_dhcp_rc=0
wifi_sta_default_route_iface=wlan0
ncm_recovery_preserved_after_dhcp=1
wifi_sta_gateway_ping_rc=0
wifi_sta_gateway_arp_state=REACHABLE
wifi_sta_gateway_arp_resolved=1
wifi_sta_dns_probe_rc=0
wifi_sta_tcp443_probe_rc=0
wifi_sta_decision=wifi-sta-pass
wifi_sta_secret_values_logged=0
```

No D-public tunnel was started in this unit:

```text
tunnel_process_alive=0
tunnel_url_observed=0
tunnel_decision=manual
```

## Native Materialization Note

The pre-handoff gate exposed a stateful driver edge:

```text
before reboot:  wlan0_present=1 flags=0x1002 link_up_rc=-1 link_up_errno=22
after cleanup:  wlan0_present=1 flags=0x1002 link_up_rc=-1 link_up_errno=22
after reboot:   wlan0 initially absent, then iftype-probe materialized it
                wlan0_wait_elapsed_ms=89655 link_up_rc=0 link_up_errno=0
                flags=0x1003 decision=softap-iftype-probe-pass
```

So the safe operational sequence for the next Wi-Fi public test is:

```text
fresh native boot
  -> WSTA2 native materialization gate with iftype probe
  -> require wlan0_admin_up=true
  -> switch_root to userdata appliance
```

Do not skip the WSTA2 gate just because `wlan0` exists; `flags=0x1002` is not enough.

## Source Changes

- `a90_dpublic_wifi_sta.sh` now requires `wpa_cli`, waits for the control socket, sends the
  known-good control commands, and records bounded `wifi_sta_ctrl_*` markers.
- `prepare_wsta3_sta_rootfs.py` treats `wpa_cli` as a required STA tool for private WSTA rootfs
  preparation.
- Tests pin the new helper/control markers and rootfs tool requirement.

## Safety Boundary

- No boot image was built or flashed.
- No forbidden partition was written.
- `userdata` was formatted/populated only through the existing D4 appliance guard path, with the
  verified `userdata` target and journaled ext4 formatter already required by the D4C gates.
- No public tunnel was started and no public URL was observed.
- No SSID, PSK, BSSID, MAC, concrete private IP, gateway, DHCP lease, public URL, or token is
  committed.
- After the Debian test, the device was rebooted back to native V3384 and final `selftest` returned
  `fail=0`.

## Validation

```text
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_wifi_sta.sh

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  tests/test_dpublic_smoke_helpers.py \
  tests/test_prepare_wsta3_sta_rootfs.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_dpublic_smoke_helpers \
  tests.test_prepare_wsta3_sta_rootfs \
  tests.test_server_distro_wifi_sta_upstream_plan
```

Live validation used the private WSTA7 rootfs tarball staged under the run dir, the no-flash WSTA2
materialization runner, D4 guarded userdata format/populate, Debian `switch_root`, SSH over USB/NCM,
and a final reboot back to native.

## Next

WSTA8 should retry D-public over Wi-Fi: start the local smoke service and the Debian-owned outbound
tunnel only after `wifi-sta-pass`, confirm the tunnel route is `wlan0`, keep USB/NCM recovery
reachable, and keep the tunnel URL in private run artifacts only.
