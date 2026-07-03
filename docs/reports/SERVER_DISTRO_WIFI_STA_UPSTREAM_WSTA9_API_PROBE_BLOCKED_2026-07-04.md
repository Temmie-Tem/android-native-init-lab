# Server-Distro WSTA9 API Probe Blocked

- Date: 2026-07-04
- Scope: D-public device-side DNS/HTTPS API probe after WSTA8 quick-tunnel block
- Native resident: `0.11.140 (v3384-server-distro-hardware-contract)`
- Public exposure: not started
- Final device state: native V3384, `selftest fail=0`

## Summary

WSTA9 added a manual Debian-side API probe for the Cloudflare quick-tunnel endpoint and
proved the previous tunnel retry should not proceed yet. The independent probe did not
reach API POST success: it failed at the device DNS/TCP layer with default route still
reported on `wlan0`.

The sharper live result is that the no-clock appliance can reach an initial
`wifi-sta-pass`, but upstream L3 did not remain stable long enough for the API probe.
After the first pass, the probe recorded:

```text
api_probe_default_route_iface=wlan0
api_probe_resolv_nameserver_count=2
api_probe_dns_control_rc=2
api_probe_dns_api_rc=2
api_probe_tcp_tool=nc.openbsd
api_probe_tcp_control_rc=1
api_probe_tcp_api_rc=1
api_probe_wget_present=1
api_probe_wget_post_rc=4
api_probe_wget_success_json=0
api_probe_openssl_post_rc=1
api_probe_openssl_success_json=0
api_probe_decision=api-dns-failed
api_probe_secret_values_logged=0
```

Cloudflared was not retried because the independent API POST was not proven.

## Live Steps

- Prepared a WSTA9 userdata rootfs with D-public binaries, the manual API probe helper,
  and `wget` staged for the probe path.
- Uploaded the tarball to SD runtime and verified the device SHA matched the host SHA
  `3888e9b2cbadc289712aeb4743095c124b75eeef10e65d305c179ebfea298bbe`.
- Used the D4 guarded same-session preflight/format/populate path for `userdata`.
- Injected the private runtime SSH public key into the mounted appliance rootfs.
- Rebooted native V3384, reran WSTA2 materialization, and confirmed `wlan0_present=1`.
- Switched into the no-clock Debian appliance.
- Confirmed Debian firstboot reached:

```text
dropbear_started=1
smoke_started=1
hud_started=1
wifi_sta_default_route_iface=wlan0
ncm_recovery_preserved_after_dhcp=1
wifi_sta_gateway_ping_rc=0
wifi_sta_gateway_arp_resolved=1
wifi_sta_dns_probe_rc=0
wifi_sta_tcp443_probe_rc=0
wifi_sta_decision=wifi-sta-pass
tunnel_decision=manual
```

- Ran `/usr/local/bin/a90-dpublic-api-probe` manually.
- Ran a no-clock manual STA refresh and repeated the API probe.
- Rebooted back to native V3384 and verified `selftest fail=0`.

## Findings

- The API probe is additive and manual. It does not start `cloudflared`, does not expose
  a public URL, and writes raw API responses only under `/run/a90-dpublic` with mode
  `0600`.
- The initial firstboot STA path still reaches a real L3 pass.
- At API-probe time, the gateway neighbor degraded and numeric external TCP failed, so
  the API failure is not yet specific to `api.trycloudflare.com`.
- A manual STA refresh produced a latest marker segment ending in `wpa_state=DISCONNECTED`,
  `wifi_sta_carrier_up=0`, and `wifi_sta_decision=wifi-sta-assoc-failed`.
- Therefore the next blocker is Debian STA/L3 persistence, not cloudflared URL parsing or
  wall-clock mutation.

## Hygiene

- No SSID, PSK, BSSID, MAC, DHCP lease, Wi-Fi private address, gateway, DNS server, public
  tunnel URL, or raw API response is recorded in this report.
- Raw transcripts and API response files remain under `workspace/private/runs/`.
- The device ended on native V3384 with `selftest: pass=12 warn=1 fail=0`.

## Next

WSTA10 should target Debian STA persistence before another D-public tunnel attempt:

- capture timestamped marker phases so old pass markers cannot obscure the latest state;
- record redacted `wpa_cli status` and association event transitions after firstboot;
- add a bounded gateway keepalive or reassociation policy only if the trace proves link
  drop or gateway ARP loss;
- retry the API probe only after the same boot shows stable gateway/DNS/TCP for a dwell
  window.
