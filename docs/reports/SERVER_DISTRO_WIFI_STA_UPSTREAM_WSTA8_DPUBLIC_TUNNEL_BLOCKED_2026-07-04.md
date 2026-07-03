# Server-Distro Wi-Fi STA Upstream WSTA8 D-Public Tunnel Blocked

- Date: `2026-07-04`
- Decision: `wsta8-wifi-pass-dpublic-tunnel-blocked`
- Native resident: `A90 Linux init 0.11.140 (v3384-server-distro-hardware-contract)`
- Device ending state: native V3384, `selftest fail=0`
- Private run dir: `workspace/private/runs/server-distro/wsta8-dpublic-wifi-live-20260703T200157Z`

## Result

WSTA8 did not publish the D-public smoke endpoint through a public tunnel.  The Wi-Fi side
passed again, but `cloudflared` quick tunnel startup is blocked at the Cloudflare quick-tunnel API
request from the device.

The accepted no-clock control path was:

```text
fresh native V3384 boot
-> WSTA2 materialization gate
-> D4 guarded no-clock WSTA8 userdata format/populate
-> switch_root to Debian appliance
-> Debian firstboot Wi-Fi STA helper
```

The Debian marker reached the expected Wi-Fi/L3 pass state:

```text
dropbear_started=1
smoke_started=1
hud_started=1
wifi_sta_ctrl_status_wpa_state=COMPLETED
wifi_sta_ctrl_status_key_mgmt=WPA2-PSK
wifi_sta_carrier_up=1
wifi_sta_dhcp_rc=0
wifi_sta_default_route_iface=wlan0
wifi_sta_gateway_ping_rc=0
wifi_sta_gateway_arp_resolved=1
wifi_sta_dns_probe_rc=0
wifi_sta_tcp443_probe_rc=0
wifi_sta_decision=wifi-sta-pass
```

The D-public tunnel did not pass:

```text
cloudflared IPv4/http2 retry: process_alive=0, public_url_present=0, has_timeout=True
device openssl API POST: DNS lookup failed before TLS/HTTP
public resolver override: DNS still failed, public_url_present=0
time-set retry: public_url_present=0, has_timeout=True, gateway ping degraded
host control POST to the same API: HTTP 200 in about 3.2s
```

No public smoke response through a tunnel was observed.

## Important Findings

1. The WSTA7 operational sequence is still required and still works: fresh native boot,
   WSTA2 `iftype-probe`, then `switch_root`.
2. A transient clock-seeded rootfs attempt was bad for this Wi-Fi path.  It reached Debian
   and started smoke/HUD, but `wpa_state=DISCONNECTED`, scan results stayed empty, and manual
   recovery eventually degraded to `wifi-sta-link-up-failed`.  The no-clock control immediately
   returned to `wifi-sta-pass`.
3. The previous quick URL detector was too broad: it could match the API endpoint
   `api.trycloudflare.com` and overstate `url_observed`.  The source now accepts only generated
   trycloudflare subdomains, excludes the API hostname, and records `quick-url-dead` if the URL is
   seen after the process exits.
4. The blocker is now above WSTA7: Wi-Fi STA and local D-public smoke/HUD are working; public
   tunnel startup needs a device-side DNS/HTTPS/cloudflared diagnostic unit before it can be called
   pass.

## Source Changes

- `prepare_wsta3_sta_rootfs.py` can stage the D-public private binaries into a WSTA rootfs:
  `cloudflared`, smoke HTTP server, local HTTP getter, and Debian HUD.  It can also explicitly
  enable the quick tunnel marker, but WSTA8 live kept quick tunnel in manual mode.
- `a90_dpublic_wifi_sta.sh` now waits for `wpa_state=COMPLETED` before DHCP and fails closed as
  `wifi-sta-assoc-failed` or `wifi-sta-ctrl-unavailable` instead of drifting into misleading DHCP
  failures.
- `a90_dpublic_firstboot.sh` now filters quick-tunnel URL detection so the API endpoint is not
  mistaken for a public quick URL.

## Safety Boundary

- No boot image was built or flashed.
- No forbidden partition was written.
- `userdata` was formatted/populated only through the existing D4 appliance guard path, with the
  verified `userdata` target and journaled ext4 formatter.
- No public URL, SSID, PSK, BSSID, MAC, gateway, DHCP lease, concrete private IP, tunnel secret, or
  token is committed.
- Raw tunnel/API logs and any generated hostname/secret remain under `workspace/private/`.
- The device was rebooted back to native V3384 and final `selftest` returned `fail=0`.

## Validation

```text
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh
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

## Next

WSTA9 should be a device-side DNS/HTTPS/cloudflared diagnostic unit, not another WSTA association
unit:

1. Keep the same fresh native boot -> WSTA2 -> no-clock Debian handoff sequence.
2. Add a small static HTTPS/API POST probe or stage a known curl/wget tool so the quick-tunnel API
   can be tested independently of `cloudflared`.
3. Compare resolver behavior for `cloudflare.com` vs `api.trycloudflare.com` before any wall-clock
   mutation.
4. Do not seed or jump wall clock before Wi-Fi; current evidence shows that path can destabilize
   WLAN/DNS.
