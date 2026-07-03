# Server-Distro WSTA17 Handoff Materialization Blocked

- Date: 2026-07-04
- Scope: Debian post-handoff WLAN reset/materialization below credentials
- Native resident: `0.11.140 (v3384-server-distro-hardware-contract)`
- Public exposure: not started
- Final device state: native V3384, `selftest fail=0`

## Summary

WSTA17 extended the WSTA16 immediate snapshot path with bounded Debian-side WLAN
materialization branches.  The test stayed below credentials, `wpa_supplicant`, association,
DHCP, gateway probing, API probing, and cloudflared.

Live result: native STA-only scan materialized `wlan0` and visible BSS before handoff, but
Debian could not make the preserved interface scan-usable.  Initial Debian state was not
rfkill-blocked and had one phy plus a `/proc/net/wireless` row, but direct `iw scan` still
returned rc `234`.  A link down/up cycle made the state worse: link down returned rc `0`,
but link up returned rc `2` with `RTNETLINK answers: Invalid argument`; afterward direct
scan returned rc `156` with `Network is down (-100)`.  Reasserting managed type succeeded,
but link up still failed.  `rfkill` CLI was absent, while sysfs rfkill already showed WLAN
unblocked.  No branch restored scan results.

## Source Changes

- `a90_dpublic_wifi_sta.sh`
  - adds `sample_handoff_state()` for redacted rfkill/phy/proc-wireless state;
  - adds `direct_iw_probe()` to record link state, handoff state, direct `iw` scan rc, BSS
    count, and pass/fail booleans;
  - extends snapshot-only mode with `try_handoff_materialization()` branches:
    `link-cycle`, `managed-reassert`, and `rfkill-unblock`;
  - requires both `iw_scan_rc=0` and BSS count `>0` for a scan pass.
- `prepare_wsta3_sta_rootfs.py`
  - records `handoff_materialization_present` in private rootfs summaries.
- Tests assert the new marker surface and helper metadata.

## Static Validation

```text
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_wifi_sta.sh

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  tests/test_prepare_wsta3_sta_rootfs.py \
  tests/test_dpublic_smoke_helpers.py

PYTHONPATH=tests python3 -m unittest \
  tests/test_prepare_wsta3_sta_rootfs.py \
  tests/test_dpublic_smoke_helpers.py

Ran 28 tests in 0.009s
OK
```

## Artifact Preparation

Prepared and uploaded a credential-free, SD-backed WSTA17 image:

```text
run_dir=workspace/private/runs/server-distro/wsta17-handoff-materialization-20260703T2337Z
mode=immediate-snapshot-only
handoff_materialization_present=true
image_sha256=9a4f410c4c572db229517b617b9f43865088fc3021ad3e6270a5095611fbde5e
remote_sha_match=true
```

No boot flash ran for WSTA17.  No userdata format/populate path ran.

One first `switch_root` attempt reached rootfs mount/display handoff but timed out before
`exec_switch_root_now`.  Because the image had been mounted rw, the SD image SHA changed and
the next attempt correctly stopped at `sha-mismatch`.  The local keyed image was reuploaded,
remote SHA matched again, and the subsequent 90s handoff reached `exec_switch_root_now`.

## Live Evidence

Native pre-handoff gate:

```text
decision=wsta15-native-sta-only-scan-engine-ok
attempts_completed=11
attempts 1-10: wifi-scan-link-up-failed / link_up_errno=19
attempt 11: wifi-scan-pass scan_result_count=11
selftest_fail_zero=true
```

Debian immediate state before reset branches:

```text
pid1_comm=init
dropbear_started=1
wifi_sta_immediate_snapshot_only=1
wifi_sta_wlan0_present=1
wifi_sta_handoff_immediate_before_link_up_rfkill_wifi_unblocked=1
wifi_sta_handoff_immediate_before_link_up_rfkill_wifi_blocked=0
wifi_sta_handoff_immediate_before_link_up_phy_count=1
wifi_sta_handoff_immediate_before_link_up_proc_wireless_row_present=1
wifi_sta_reg_immediate_before_link_up_iw_scan_rc=234
wifi_sta_reg_immediate_after_link_up_iw_scan_rc=234
```

Materialization branches:

```text
branch_order=link-cycle,managed-reassert,rfkill-unblock

link-cycle:
  down_rc=0
  up_rc=2
  scan_after_down_rc=156
  scan_after_up_rc=156

managed-reassert:
  set_type_managed_rc=0
  up_rc=2
  scan_after_up_rc=156

rfkill-unblock:
  rfkill_unblock_rc=127
  link_up_rc=2
  scan_after_up_rc=156

pass_branch=none
wifi_sta_decision=wifi-sta-handoff-materialization-scan-failed
tunnel_wifi_sta_gate_ok=0
```

Manual stderr confirmation after the branches:

```text
ip link set wlan0 up:
  rc=2
  stderr=RTNETLINK answers: Invalid argument

iw dev wlan0 scan:
  rc=156
  stderr=command failed: Network is down (-100)

iw dev wlan0 info:
  rc=0
  type=managed
```

The device was rebooted from Debian and returned to native V3384:

```text
version=0.11.140 build=v3384-server-distro-hardware-contract
selftest: pass=12 warn=1 fail=0
```

## Interpretation

This is no longer a missing interface, missing phy, missing `iw`, or rfkill block.  Debian
can see a managed `wlan0` and the WLAN rfkill is unblocked, but nl80211 scan is invalid
while the link is administratively up.  Once Debian cycles the link down, it cannot bring
the interface back up at all; the kernel rejects the up transition with `EINVAL`.

The next useful boundary is the handoff control plane, not more link toggling:

1. capture post-handoff process inventory for WLAN companion processes and compare it with
   native pre-handoff state;
2. capture focused dmesg around the first `iw scan` and first `ip link set up` failure;
3. determine whether Debian needs preserved vendor WLAN helper processes or a native-owned
   Wi-Fi service boundary instead of direct Debian netdev ownership;
4. keep credentials, association, DHCP, API, and tunnel work parked.

## Hygiene

- No public tunnel was started.
- No association, DHCP, gateway ping, DNS, API POST, or cloudflared path ran.
- No Wi-Fi SSID, PSK, BSSID, MAC, DHCP lease, private Wi-Fi address, gateway, DNS server,
  public URL, or generated hostname is recorded in this report.
- Raw transcripts, SSH keys, and images remain under `workspace/private/runs/`.
- The device ended on native V3384 with `selftest: pass=12 warn=1 fail=0`.
