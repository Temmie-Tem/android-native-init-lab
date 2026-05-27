# V1130 PM Observer Modem Holder Helper Build Report

Date: `2026-05-27`

## Result

- Decision: `v1130-pm-observer-modem-holder-helper-build-pass`
- Pass: `true`
- Evidence: `tmp/wifi/v1130-execns-helper-v213-build/manifest.json`
- Summary: `tmp/wifi/v1130-execns-helper-v213-build/summary.md`
- Helper artifact: `tmp/wifi/v1130-execns-helper-v213-build/a90_android_execns_probe`
- Helper marker: `a90_android_execns_probe v213`
- Helper sha256:
  `d1c354b2b089ede50cc53d452666d119e9151b1e97b7bb1344dbd0431bd69356`
- Build runner: `scripts/revalidation/native_wifi_pm_observer_modem_holder_helper_build_v1130.py`

## Summary

V1130 adds a scoped modem pre-holder path to
`wifi-companion-pm-service-trigger-observer`.

New flags:

```text
--allow-pm-observer-modem-pre-holder
--pm-observer-modem-pre-holder
```

The holder is deliberately narrow:

```text
mode: wifi-companion-pm-service-trigger-observer only
target: /dev/subsys_modem only
open flags: O_RDONLY | O_NONBLOCK | O_CLOEXEC
plain retry: disabled
```

The holder starts before `pm_proxy_helper`, so the next live gate can test the
first-opener contract while preserving the V1128/V1129 provider-positive CNSS
order.

## Build Checks

The V1130 build runner checked:

```text
v1129 input decision/pass
source strings
static aarch64 build
no PT_INTERP
binary marker and safety strings
```

Result:

```text
decision: v1130-pm-observer-modem-holder-helper-build-pass
pass: True
sha256: d1c354b2b089ede50cc53d452666d119e9151b1e97b7bb1344dbd0431bd69356
```

## Safety

V1130 was source/build only:

```text
device_commands_executed=false
deploy_executed=false
tracefs_write_executed=false
pm_actor_executed=false
cnss_daemon_start_executed=false
wifi_hal_start_executed=false
scan_connect_executed=false
credential_use_executed=false
dhcp_route_executed=false
external_ping_executed=false
wifi_bringup_executed=false
reboot_executed=false
```

The implementation does not add `/dev/subsys_esoc0`, eSoC ioctl/control,
Wi-Fi HAL, scan/connect, credentials, DHCP/route, external ping, partition
write, boot image write, or flash behavior.

## Next

V1131 should deploy helper `v213` and run the bounded live gate:

1. V401/V490 current-boot policy-load precondition;
2. global firmware mounts;
3. PM observer with modem pre-holder enabled;
4. CNSS PM register/connect replay;
5. lower mss/mdm3/WLFW/`wlan0` classification;
6. cleanup reboot if any holder or PM actor is not proven stopped.

Do not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/route, or
send external ping until the lower modem/eSoC path advances.
