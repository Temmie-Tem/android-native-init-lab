# Native Init V507 Dual-HAL CNSS Context Report

Date: 2026-05-21

## Summary

V507 advanced the native-init Wi-Fi bring-up path by removing an unsafe Wi-Fi
HAL capability grant, adding runtime-gap instrumentation, and proving that
`cnss-daemon` can be launched with the Android-observed SELinux execution
context.

The first-connect objective is still not complete: `IWifi/default` did not
register, and no `wlan0`/`phy`/`/dev/wlan` surface appeared.

## Implemented

- Updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper
  `a90_android_execns_probe v57`.
- Removed ambient `CAP_SYS_MODULE` from the Wi-Fi HAL identity contract.
- Added child `/proc/<pid>/attr/current` capture for composite HAL children.
- Added host/private Wi-Fi runtime path snapshots for:
  - `/dev/socket/wifihal`
  - `/dev/socket/wifihal/wifihal_ctrlsock`
  - `/dev/socket/wpa_wlan0`
  - `/dev/wlan`
  - `/data/vendor/wifi`
  - `/data/vendor/wifi/sockets`
  - `/data/vendor/wifi/sockets/wlan0`
  - `/sys/class/net/wlan0`
- Added Android-observed default exec context for `cnss-daemon`:
  `u:r:vendor_wcnss_service:s0`.
- Added deployment/proof wrappers:
  - `scripts/revalidation/wifi_execns_helper_v56_deploy_preflight.py`
  - `scripts/revalidation/native_wifi_dual_hal_runtime_gap_v506.py`
  - `scripts/revalidation/wifi_execns_helper_v57_deploy_preflight.py`
  - `scripts/revalidation/native_wifi_dual_hal_cnss_context_v507.py`

## Validation

Static build:

```text
tmp/wifi/v507-a90_android_execns_probe-v57/a90_android_execns_probe
sha256: 9ae5562727682a9811df7216fb522e4e1dd7271b4f5c4ca4ecf6545bb8be9afa
static: yes, no dynamic section
```

Safety checks:

```text
rg CAP_SYS_MODULE stage3/linux_init/helpers/a90_android_execns_probe.c
no matches
```

Deploy:

```text
tmp/wifi/v507-helper-v57-deploy-20260521-094326/
decision: execns-helper-v57-deploy-pass
wifi_bringup_executed: False
```

Live bounded proof:

```text
tmp/wifi/v507-cnss-context-run-20260521-094349/
decision: v507-dual-hal-cnss-context-captured
pass: True
reason: IWifi/default still not registered; helper_result=service-query-runtime-gap micro_result=service-query-timeout
wifi_bringup_executed: False
```

Postflight:

```text
status: rc=0 status=ok
selftest: pass=11 warn=1 fail=0
```

## Evidence

V506 before CNSS context repair:

```text
tmp/wifi/v506-runtime-gap-run-20260521-093926/
decision: v506-dual-hal-runtime-gap-captured
cnss attr/current: u:r:kernel:s0
wlan_count: 0
phy_count: 0
```

V507 after CNSS context repair:

```text
tmp/wifi/v507-cnss-context-run-20260521-094349/
cnss selinux_exec.target_context: u:r:vendor_wcnss_service:s0
cnss attr/current: u:r:vendor_wcnss_service:s0
IWifi/default: lshal wait timeout
wlan_count: 0
phy_count: 0
```

Runtime surfaces still absent during V507:

```text
/dev/socket/wifihal: missing
/dev/socket/wifihal/wifihal_ctrlsock: missing
/dev/socket/wpa_wlan0: missing
/dev/wlan: missing
/data/vendor/wifi/sockets/wlan0: missing
/sys/class/net/wlan0: missing
```

Kernel log after the run showed `cnss-daemon` reaching the `cld80211` generic
netlink family, but still no `wlan0` creation:

```text
ctrl_getfamily found w/o mod res: cld80211
reply err: 0
```

## Interpretation

V507 resolves one concrete mismatch with Android boot-complete: `cnss-daemon`
now runs in `u:r:vendor_wcnss_service:s0` instead of `u:r:kernel:s0`.

That did not make `IWifi/default` appear. The remaining blocker is lower than
HIDL registration: the native run still lacks the runtime device/network
surfaces that Android has before stable Wi-Fi control:

- no `/dev/wlan`;
- no `wlan0` or `phy*`;
- no wifihal control socket;
- no wpa control socket.

This suggests the next useful gate is not credentialed Wi-Fi connect yet. The
next gate should isolate the minimal safe driver/runtime surface required to
make `wlan0` appear, without granting module-load capability to the HAL and
without starting supplicant or connecting to an AP.

## Next

Recommended V508:

1. Add a bounded native `wlan0` materialization probe that starts only the
   minimum CNSS/HAL stack already used here.
2. Capture pre/during/post `dmesg`, `genl`, `/proc/net/dev`,
   `/sys/class/net`, `/sys/class/ieee80211`, `/dev/wlan`, and relevant CNSS
   sockets.
3. Explicitly compare with V431 Android boot-complete surfaces.
4. Keep blocked:
   - `CAP_SYS_MODULE` to Wi-Fi HAL;
   - `cnss_diag`;
   - `wpa_supplicant`;
   - `wificond`;
   - scan/connect/DHCP/external ping.

Only after `wlan0`/`phy` appears should the project advance to scan-only, then
SSID connect, then external ping.
