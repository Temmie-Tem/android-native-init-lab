# Server-Distro WSTA16 Immediate Handoff Scan Blocked

- Date: 2026-07-04
- Scope: immediate Debian post-`switch_root` WLAN scan boundary below association
- Native resident: `0.11.140 (v3384-server-distro-hardware-contract)`
- Public exposure: not started
- Final device state: native V3384, `selftest fail=0`

## Summary

WSTA16 tested the exact handoff boundary left by WSTA15.  WSTA15 proved that a fresh
native V3384 boot can materialize `wlan0` and see visible BSS with a STA-only native
`wifi scan` gate.  WSTA16 then switched to an SD-backed Debian image that starts the
Wi-Fi helper in snapshot-only mode before `wpa_supplicant`, DHCP, gateway probing, API
probing, or cloudflared.

Live result: the handoff succeeded and Debian became PID1, but immediate Debian direct
`iw dev wlan0 scan` failed with rc `234` / kernel error `Invalid argument (-22)` and BSS
count `0`.  A bounded delayed manual probe after SSH login produced the same rc and zero
BSS count twice.  `wlan0` exists in Debian and `ip link set wlan0 up` returns rc `0`, so
the blocker is not a missing interface or missing `iw` binary.  The next target is a
bounded post-handoff WLAN reset/materialization step in Debian, not gateway/API/tunnel
work.

## Source Changes

- `a90_dpublic_wifi_sta.sh`
  - adds `/etc/a90-dpublic/wifi-sta-immediate-snapshot-only`;
  - records `wifi_sta_immediate_snapshot_only`;
  - in snapshot-only mode, avoids supplicant config, `wpa_supplicant`, DHCP, ping, API,
    and tunnel work;
  - records link and `iw` state before and after a single `ip link set wlan0 up`;
  - finishes as `wifi-sta-immediate-snapshot-pass` only if direct `iw` scan succeeds.
- `prepare_wsta3_sta_rootfs.py`
  - adds `--immediate-snapshot-only`;
  - stages only the enable flag and snapshot-only flag;
  - does not require or copy private Wi-Fi credentials in this mode.
- Tests cover the new helper mode and preparer credential-free path.

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

Ran 28 tests in 0.006s
OK
```

## Artifact Preparation

Prepared a credential-free, SD-backed WSTA16 rootfs image:

```text
run_dir=workspace/private/runs/server-distro/wsta16-immediate-snapshot-20260704T0813Z
mode=immediate-snapshot-only
config_required=false
config_target_present=false
snapshot_only_target=etc/a90-dpublic/wifi-sta-immediate-snapshot-only
```

The image was built as ext4, checked with `e2fsck -fn`, then a private SSH key was injected
for observation only.  The keyed image was uploaded to the SD runtime path and verified by
SHA-256:

```text
image_sha256=b8f0f98ea24875e5daada9d17ecfd62067ff316129308c83bda6d54910dac58a
remote_sha_match=true
```

No boot flash ran for WSTA16.  No userdata format/populate path ran.

## Live Evidence

Pre-handoff native gate:

```text
first short gate:
  decision=wsta15-native-sta-only-scan-engine-blocked
  attempts=6
  all attempts: wifi-scan-link-up-failed / link_up_errno=19

extended gate, same boot:
  decision=wsta15-native-sta-only-scan-engine-ok
  attempts=5
  attempts 1-4: wifi-scan-link-up-failed / link_up_errno=19
  attempt 5: wifi-scan-pass scan_result_count=11
  forbidden_native_workers=[]
  selftest_fail_zero=true
```

`switch_root` handoff:

```text
expected_sha_match=1
rootfs=mounted
distro_init=ok
handoff_display=done
exec_switch_root_now=observed
```

Debian observation over the local recovery SSH path:

```text
marker=A90DPUBLIC_MARKER
pid1_comm=init
dropbear_started=1
wifi_sta_immediate_snapshot_only=1
wifi_sta_config_required=0
wifi_sta_config_present=0
wifi_sta_wlan0_present=1
wifi_sta_immediate_link_set_up_rc=0
wifi_sta_reg_immediate_before_link_up_iw_scan_rc=234
wifi_sta_reg_immediate_before_link_up_iw_scan_bss_count=0
wifi_sta_reg_immediate_after_link_up_iw_scan_rc=234
wifi_sta_reg_immediate_after_link_up_iw_scan_bss_count=0
wifi_sta_immediate_iw_scan_rc=234
wifi_sta_immediate_iw_scan_bss_count=0
wifi_sta_decision=wifi-sta-immediate-snapshot-scan-failed
tunnel_wifi_sta_gate_ok=0
```

Delayed manual Debian checks stayed blocked:

```text
scan1_rc=234
scan1_bss=0
scan1_err=command failed: Invalid argument (-22)
scan2_rc=234
scan2_bss=0
scan2_err=command failed: Invalid argument (-22)
```

The device was rebooted from Debian and returned to native V3384:

```text
version=0.11.140 build=v3384-server-distro-hardware-contract
selftest: pass=12 warn=1 fail=0
```

## Interpretation

WSTA16 closes the ambiguity between "native cannot see Wi-Fi" and "Debian loses the usable
scan state after handoff."  Native can see visible BSS immediately before handoff, but the
Debian image cannot run a direct nl80211 scan even before supplicant starts.  The preserved
interface is present but not scan-usable.

The next unit should stay below credentials and association and test controlled Debian-side
materialization/reset options, for example:

1. inspect and record post-handoff rfkill, phy, netdev, and nl80211 state;
2. run a bounded link-down/link-up cycle and rescan;
3. if available and safe, test a bounded managed-type reassertion or phy rescan trigger;
4. reboot back to native after each bounded branch and keep public tunnel/API work parked.

## Hygiene

- No public tunnel was started.
- No association, DHCP, gateway ping, DNS, API POST, or cloudflared path ran.
- No Wi-Fi SSID, PSK, BSSID, MAC, DHCP lease, private Wi-Fi address, gateway, DNS server,
  public URL, or generated hostname is recorded in this report.
- Raw transcripts, SSH keys, and images remain under `workspace/private/runs/`.
- The device ended on native V3384 with `selftest: pass=12 warn=1 fail=0`.
