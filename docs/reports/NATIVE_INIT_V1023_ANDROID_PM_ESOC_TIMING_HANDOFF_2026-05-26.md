# V1023 Android PM/eSoC Timing Handoff

- date: `2026-05-26`
- scope: bounded Android handoff + V1022 read-only capture
- decision: `v1023-android-pm-esoc-timing-captured-rollback-complete`
- pass: `True`
- evidence: `tmp/wifi/v1023-android-pm-esoc-timing-handoff-live-20260526-180151/manifest.json`

## Summary

V1023 successfully captured Android-good PM/eSoC timing evidence and restored
native init v724.

The first ADB-window V1022 run was too early to capture the full PM/eSoC → WLFW
continuation. The boot-complete fallback run captured the complete dmesg
continuation through WLFW, firmware-ready, and `wlan0`, but still missed exact
`vendor.per_proxy_helper` fd ownership.

## Result

| Item | Result |
| --- | --- |
| Android boot image flash/readback | pass |
| first Android ADB wait | pass |
| V1022 early sampler | `v1022-android-pm-esoc-timing-incomplete` |
| Android boot-complete | pass |
| V1022 late sampler | `v1022-android-pm-esoc-timing-captured-fd-window-missed` |
| native v724 flash/readback | pass |
| native `BOOT OK` after rollback | pass |
| Wi-Fi command / credential / external ping | not executed |

## Android Timing

From the V1022 late sampler:

| Marker | Time |
| --- | ---: |
| `vendor.per_proxy_helper` start | `5.854388s` |
| `vendor.per_mgr` start | `6.996837s` |
| `vendor.per_proxy` start | `7.933998s` |
| `vendor.mdm_helper` start | `8.333351s` |
| `cnss-daemon wlfw_start` | `8.454800s` |
| `/dev/subsys_esoc0` get | `8.517767s` |
| `msm/modem/wlan_pd` indication | `9.466862s` |
| `icnss_qmi: QMI Server Connected` | `9.469315s` |
| `WLAN FW is ready` | `14.510475s` |
| `wlan0` event | `15.204582s` |

Readable Android GPIO surfaces were present for GPIO135, GPIO142, and PMIC
GPIO9, but the repeated process/fd sampler still did not catch
`vendor.per_proxy_helper` holding `/dev/subsys_esoc0`.

## Interpretation

The Android-good chain is now captured in the same handoff:

```text
vendor.per_proxy_helper/per_mgr/per_proxy
  -> vendor.mdm_helper
  -> cnss-daemon wlfw_start
  -> /dev/subsys_esoc0 get
  -> WLAN-PD indication
  -> ICNSS QMI connected
  -> WLAN FW ready
  -> wlan0
```

The exact fd ownership window is still missing because `vendor.per_proxy_helper`
is a short-lived oneshot and ADB userland collection begins after the critical
fd transition. This makes another ADB-only retry low value unless it starts
before Android userspace completes the PM/eSoC handoff.

## Guardrails

- no native `/dev/subsys_esoc0` retry
- no `/dev/esoc-*` ioctl
- no GPIO/sysfs/debugfs write
- no Wi-Fi command, scan/connect/link-up, credential use, DHCP/route, or external ping
- Android boot write was followed by native v724 readback and native `BOOT OK`

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/android_pm_esoc_timing_handoff_v1023.py
python3 scripts/revalidation/android_pm_esoc_timing_handoff_v1023.py --allow-android-boot-flash --assume-yes --i-understand-native-rollback dry-run
git diff --check
```

Live result:

```text
decision: v1023-android-pm-esoc-timing-captured-rollback-complete
pass: True
native_rollback_verified: True
wifi_command_executed: False
external_ping_executed: False
```

Current native status after rollback:

```text
boot: BOOT OK shell
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

## Next

Proceed to V1024 as a host-only classifier for the early-capture gap. The likely
next implementation route is a minimal Magisk/post-fs-data read-only sampler or
another Android-side pre-ADB mechanism, because late ADB captures full dmesg but
not the exact oneshot fd ownership window.

