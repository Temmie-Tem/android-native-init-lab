# Server-Distro WSTA12 Gateway Diagnostic Association Blocked

- Date: 2026-07-04
- Scope: gateway reachability diagnostic markers plus association retry diagnostics
- Native resident: `0.11.140 (v3384-server-distro-hardware-contract)`
- Public exposure: not started
- Final device state: native V3384, `selftest fail=0`

## Summary

WSTA12 added the gateway-boundary diagnostics requested after WSTA11: each L3/dwell sample
now records gateway ping attempt count, successes, timing, neighbor state before/after a
bounded `ip neigh get`, DHCP lease-router presence/match, and default-route gateway
presence/match.  These markers do not print private gateway, lease, DNS, SSID, PSK, BSSID,
MAC, or public URL values.

Live validation did not reach the gateway dwell boundary.  After a successful native
materialization gate and D4 userdata refresh, Debian failed earlier at association.  A
hot-patched helper with bounded association retry diagnostics showed three association
attempts, all with `SCAN_RESULTS` count `0`, `wpa_state=DISCONNECTED`, carrier down, and
`wifi_sta_decision=wifi-sta-assoc-failed`.

No API probe or cloudflared retry was run.

## Source Changes

- `a90_dpublic_wifi_sta.sh`
  - adds `default_route_gateway`;
  - records per-sample gateway ping attempts, successes, first-success timing, and total
    timing;
  - records gateway neighbor state before `ip neigh get`, the `ip neigh get` return code,
    and neighbor state after that lookup and after ping;
  - records DHCP lease-router presence/match and default-route gateway presence/match as
    booleans only;
  - adds bounded association retry diagnostics: up to three 20-second attempts, with
    attempt-state and scan-results count markers, and bounded retry
    `SCAN -> ENABLE_NETWORK -> SELECT_NETWORK -> REASSOCIATE`.
- `prepare_wsta3_sta_rootfs.py`
  - records `gateway_dwell_present` and `assoc_retry_present` for private rootfs summaries.
- Tests now assert the new gateway and association-retry marker surface.

## Live Evidence

The live unit used the same guarded path as WSTA11:

```text
native V3384 -> WSTA2 materialization -> WSTA12 private rootfs -> SD upload
-> D4 guarded format/populate -> Debian switch_root -> marker collection
```

WSTA2 details:

```text
initial short timeout: stale/early materialization checks failed
native reboot: V3384, selftest fail=0
default WSTA2 timeout: wsta2-native-materialization-pass
wlan0_wait_elapsed_ms=54634
wlan0_present=1
link_up_rc=0
decision=softap-iftype-probe-pass
```

D4 userdata refresh:

```text
format=done formatter=e2fsprogs-mkfs.ext4 node=/dev/block/a90-userdata label=A90D4ROOT has_journal=1
populate=done root=/mnt/a90-userdata-root marker=userdata=appliance-root
```

The first `switch_root` attempt stopped at display-owner cleanup with `EBUSY`.  Native
remained healthy, `autohud` was then stopped, and the second `switch_root` reached
`exec_switch_root_now`.

Initial Debian firstboot STA failed before dwell:

```text
wifi_sta_ctrl_status_wpa_state=DISCONNECTED
wifi_sta_wpa_completed=0
wifi_sta_wpa_completed_wait_sec=20
wifi_sta_carrier_up=0
wifi_sta_decision=wifi-sta-assoc-failed
```

Manual rerun with the original helper produced the same decision.  After hot-patching the
current source helper into Debian, the bounded association retry diagnostics showed:

```text
wifi_sta_assoc_attempts_max=3
wifi_sta_assoc_attempt_wait_sec=20
wifi_sta_assoc_attempt_1_wpa_state=DISCONNECTED
wifi_sta_assoc_attempt_1_scan_results_count=0
wifi_sta_assoc_attempt_1_completed=0
wifi_sta_assoc_attempt_1_retry_scan_rc=0
wifi_sta_assoc_attempt_1_retry_reassociate_rc=0
wifi_sta_assoc_attempt_2_wpa_state=DISCONNECTED
wifi_sta_assoc_attempt_2_scan_results_count=0
wifi_sta_assoc_attempt_2_completed=0
wifi_sta_assoc_attempt_2_retry_scan_rc=0
wifi_sta_assoc_attempt_2_retry_reassociate_rc=0
wifi_sta_assoc_attempt_3_wpa_state=DISCONNECTED
wifi_sta_assoc_attempt_3_scan_results_count=0
wifi_sta_assoc_attempt_3_completed=0
wifi_sta_wpa_completed=0
wifi_sta_wpa_completed_wait_sec=60
wifi_sta_wpa_completed_attempts=3
wifi_sta_carrier_up=0
wifi_sta_decision=wifi-sta-assoc-failed
```

Interpretation: the WSTA11 gateway problem is still real, but this WSTA12 live run could
not re-enter that state.  The immediate blocker is Debian-side scan visibility/association:
the helper can command scans and reassociation, but `SCAN_RESULTS` stays empty for three
bounded attempts.

## Hygiene

- No public tunnel was started.
- No SSID, PSK, BSSID, MAC, DHCP lease, Wi-Fi private address, gateway, DNS server, public
  URL, generated hostname, or raw API response is recorded in this report.
- Raw transcripts remain under `workspace/private/runs/`.
- The device ended on native V3384 with `selftest: pass=12 warn=1 fail=0`.

## Next

WSTA13 should target the Debian scan visibility boundary before returning to gateway
keepalive work:

- compare native `wlan0` materialization/scan state with Debian `wpa_cli SCAN_RESULTS`
  after handoff;
- capture redacted country/regulatory and scan-trigger return codes;
- determine whether Debian is missing a timing delay, firmware readiness condition,
  regulatory setup, or cleanup after the native iftype probe;
- do not retry the API probe, cloudflared, or gateway keepalive candidate until Debian can
  reliably see scan results and re-associate.
