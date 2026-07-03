# Server-Distro WSTA14 Link-State / Scan-Engine Blocked

- Date: 2026-07-04
- Scope: Debian link-state and `iw` scan-engine diagnostic after native WSTA2 materialization
- Native resident: `0.11.140 (v3384-server-distro-hardware-contract)`
- Public exposure: not started
- Final device state: native V3384, `selftest fail=0`

## Summary

WSTA14 added a stronger Debian-side boundary diagnostic for the WSTA13 failure.  The
previous result showed `wpa_cli SCAN` returning success while `SCAN_RESULTS` stayed empty
and `wlan0` remained down.  WSTA14 stages `iw`, records sysfs/ip-link state before and
after `wpa_supplicant`, runs an `iw dev wlan0 scan` count-only probe, and reasserts
`ip link set wlan0 up` after failed association retries.

Live result: native WSTA2 materialization passed, D4 guarded format/populate passed, and
Debian handoff succeeded on retry after display-owner cleanup.  In Debian, `wlan0` exists
as a wireless managed interface and is administratively UP, but it never reaches RUNNING
or LOWER_UP.  Direct `iw` scan returns rc `234` and BSS count `0`; `wpa_cli` scan windows
also stay at result count `0`; bounded relink attempts return rc `0` but do not change the
flags.  Final decision remains `wifi-sta-assoc-failed`.

This keeps the blocker below association and below L3.  Do not return to API/cloudflared
until the Debian handoff can either preserve a usable `wlan0` scan state or explicitly
reset/re-materialize the WLAN path after switch_root.

## Source Changes

- `a90_dpublic_wifi_sta.sh`
  - adds `link_snapshot()` for redacted sysfs/ip-link state;
  - records operstate, carrier, interface flags, qdisc, queue length, and wireless presence;
  - records those snapshots before link-up, after link-up, after supplicant start, after
    country handling, after scan, after reassociation, and around retry relink attempts;
  - adds count-only `iw` diagnostics: dev info, managed type, link connected flag, direct
    scan rc, and direct scan BSS count;
  - reasserts `ip link set wlan0 up` after retry scan windows as a diagnostic only.
- `prepare_wsta3_sta_rootfs.py`
  - stages `iw` as a required STA diagnostic tool;
  - records `linkstate_diag_present` and `iw_diag_present` in the private rootfs summary.
- Tests assert the new link-state and `iw` diagnostic marker surface.

During the first WSTA14 live attempt, a new shell-global variable bug caused nested marker
names.  The useful raw evidence was kept private, the bug was fixed by using separate
snapshot/regulatory label variables, and the live run was repeated before this report.

## Live Evidence

The live path was:

```text
native V3384 -> native reboot / bridge recovery for stale state
-> WSTA2 materialization -> fixed WSTA14 private rootfs
-> SD upload -> D4 guarded format/populate
-> Debian switch_root -> firstboot STA helper -> native reboot
```

WSTA2 materialization:

```text
decision=wsta2-native-materialization-pass
wlan0_wait_elapsed_ms=93659
wlan0_present=1
link_up_rc=0
decision=softap-iftype-probe-pass
```

D4 userdata refresh:

```text
format=done formatter=e2fsprogs-mkfs.ext4 node=/dev/block/a90-userdata label=A90D4ROOT has_journal=1
populate=done root=/mnt/a90-userdata-root marker=userdata=appliance-root
```

WSTA14 helper/rootfs presence:

```text
linkstate_diag_present=true
iw_diag_present=true
sta_tools.after.tools.iw.present=true
fixed_link_var_rc=0
fixed_reg_var_rc=0
iw_x_rc=0
```

Debian `iw` and link-state markers:

```text
wifi_sta_reg_after_country_iw_present=1
wifi_sta_reg_after_country_iw_reg_get_rc=0
wifi_sta_reg_after_country_iw_reg_country_present=1
wifi_sta_reg_after_country_iw_dev_info_rc=0
wifi_sta_reg_after_country_iw_phy_present=1
wifi_sta_reg_after_country_iw_type_managed=1
wifi_sta_reg_after_country_iw_link_rc=0
wifi_sta_reg_after_country_iw_link_connected=0
wifi_sta_reg_after_country_iw_scan_rc=234
wifi_sta_reg_after_country_iw_scan_bss_count=0
```

The interface remains administratively up but not running/lower-up:

```text
wifi_sta_link_after_link_up_flags_hex=0x1003
wifi_sta_link_after_link_up_flags_up=1
wifi_sta_link_after_link_up_flags_running=0
wifi_sta_link_after_link_up_flags_lower_up=0
wifi_sta_link_after_wpa_start_flags_hex=0x1003
wifi_sta_link_after_wpa_start_flags_up=1
wifi_sta_link_after_wpa_start_flags_running=0
wifi_sta_link_after_wpa_start_flags_lower_up=0
wifi_sta_link_after_reassociate_flags_hex=0x1003
wifi_sta_link_after_reassociate_flags_up=1
wifi_sta_link_after_reassociate_flags_running=0
wifi_sta_link_after_reassociate_flags_lower_up=0
```

Scan and relink attempts do not recover it:

```text
wifi_sta_scan_initial_final_results_count=0
wifi_sta_scan_retry_1_final_results_count=0
wifi_sta_assoc_attempt_1_retry_link_up_rc=0
wifi_sta_link_assoc_retry_1_after_relink_flags_hex=0x1003
wifi_sta_link_assoc_retry_1_after_relink_flags_running=0
wifi_sta_link_assoc_retry_1_after_relink_flags_lower_up=0
wifi_sta_scan_retry_2_final_results_count=0
wifi_sta_assoc_attempt_2_retry_link_up_rc=0
wifi_sta_link_assoc_retry_2_after_relink_flags_hex=0x1003
wifi_sta_link_assoc_retry_2_after_relink_flags_running=0
wifi_sta_link_assoc_retry_2_after_relink_flags_lower_up=0
wifi_sta_wpa_completed=0
wifi_sta_decision=wifi-sta-assoc-failed
```

## Interpretation

`wlan0` is not missing in Debian, and this is not a missing `iw` package or missing
wireless extension.  The phy and managed interface are visible, but the scan engine rejects
direct scan with rc `234` while the link flags remain `UP` without `RUNNING` or
`LOWER_UP`.

The next unit should focus on the handoff boundary and WLAN driver state, not gateway,
DNS, API, or tunnel behavior.  Likely WSTA15 targets:

- compare native pre-handoff scan/readiness state with immediate Debian post-handoff state;
- test whether the WSTA2 AP-iftype add/delete probe leaves the Debian scan engine in a bad
  state and whether a STA-only materialization path avoids it;
- add a bounded post-handoff WLAN reset/materialization step if needed, without leaving
  native Wi-Fi workers alive after switch_root.

## Hygiene

- No public tunnel was started.
- No SSID, PSK, BSSID, MAC, DHCP lease, Wi-Fi private address, gateway, DNS server, public
  URL, generated hostname, or raw API response is recorded in this report.
- Raw transcripts remain under `workspace/private/runs/`.
- The device ended on native V3384 with `selftest: pass=12 warn=1 fail=0`.

