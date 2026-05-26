# Native Init V966 Android WLFW Start Attribution Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| host-only classifier | `tmp/wifi/v966-android-wlfw-start-attribution/manifest.json` | `v966-android-cnss-wlfw-start-window-attributed` |

V966 uses the existing V913 Android same-boot dmesg/process evidence and V963
native comparator evidence. No Android boot, Magisk module, ADB command, serial
device command, daemon start, Wi-Fi HAL start, scan/connect, DHCP/route, external
ping, credential use, boot image write, or partition write occurred.

## Numbering

The proposed Android dmesg/Magisk direction is valid, but `V896` is already used
for the Android `mdm_helper`/`ks` image-contract classifier. The same idea is
therefore recorded here as `V966`, the next unit selected by V965.

## Implementation

- Added classifier:
  `scripts/revalidation/native_wifi_android_wlfw_start_attribution_v966.py`
- Evidence:
  `tmp/wifi/v966-android-wlfw-start-attribution/summary.md`
- Latest pointer:
  `tmp/wifi/latest-v966-android-wlfw-start-attribution.txt`

## Findings

Android orders the positive Wi-Fi bring-up window as:

| Event | Time |
| --- | --- |
| WLAN driver loading | `5.780374` |
| `vendor.wifi_hal_legacy` start | `6.732796` |
| `vendor.wifi_hal_ext` start | `6.861900` |
| `vendor.per_mgr` start | `6.910953` |
| service-notifier 180 connect | `6.975128` |
| service-notifier 74 connect | `6.976821` |
| `wificond` start | `8.045616` |
| `vendor.mdm_helper` start | `8.148170` |
| `cnss-daemon` start | `8.172571` |
| `cnss-daemon wlfw_start` | `8.349631` |
| `/dev/subsys_esoc0` `__subsystem_get` | `8.402277` |
| WLAN-PD indication | `9.414862` |
| ICNSS QMI server connected | `9.417488` |
| BDF `regdb.bin` | `9.476146` |
| BDF `bdwlan.bin` | `9.487515` |
| WLAN FW ready | `14.580127` |
| `wlan0` event | `14.950217` |

The key deltas are:

- `wlfw_start` occurs `177.060 ms` after `cnss-daemon` start.
- `wlfw_start` occurs `201.461 ms` after `vendor.mdm_helper` start.
- `wlfw_start` occurs `304.015 ms` after `wificond` start.
- `/dev/subsys_esoc0` `__subsystem_get` occurs `52.646 ms` after `wlfw_start`.
- WLAN-PD appears `1065.231 ms` after `wlfw_start`.
- `wlan0` appears `6600.586 ms` after `wlfw_start`.

## Interpretation

`wlfw_start` is not caused by the direct `/dev/subsys_esoc0` open. Android emits
`cnss-daemon wlfw_start: Starting` first, then reaches the `esoc0`
`__subsystem_get` path roughly `52 ms` later.

The existing V913 dmesg also has no `qcwlanstate` marker before `wlfw_start`.
That does not prove `qcwlanstate` is impossible, but it removes it as an observed
trigger in the available Android boot evidence.

The V963 native comparator is the negative control:

| Signal | Count |
| --- | --- |
| `cnss-daemon` netlink markers | `15` |
| `wlfw_start` markers | `0` |
| `unable to queue event for SDX50M` | `3` |
| `esoc0` `__subsystem_get` markers | `1` |

So native already reaches a CNSS netlink-visible state, but it does not enter the
Android `wlfw_start` service window. The missing piece is more likely Android
init Wi-Fi service-window parity around Wi-Fi HAL legacy/ext, `wificond`,
`mdm_helper`, `per_mgr`, and `cnss-daemon`, not another blind eSoC open.

## Magisk / Android Recapture Note

A Magisk module could still capture very early Android boot GPIO/eSoC surfaces,
but V966 does not need it yet. V913 already contains the full Android dmesg
history needed to place `wlfw_start`, `esoc0`, WLAN-PD, BDF, and `wlan0` in a
single same-boot timeline. Magisk should remain a fallback only if a future
question requires data that is absent from V913, such as denser GPIO interrupt
polling during the first seconds of Android boot.

## Guardrails

- Host-only classifier.
- No new Android handoff.
- No Magisk module.
- No ADB command.
- No serial device command.
- No daemon start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credentials.
- No DHCP/route change.
- No external ping.
- No boot image or partition write.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_wlfw_start_attribution_v966.py
python3 scripts/revalidation/native_wifi_android_wlfw_start_attribution_v966.py
```

Result:

```text
decision: v966-android-cnss-wlfw-start-window-attributed
pass: True
```

## Next

V967 should be source/build-only first: define an Android init Wi-Fi
service-window parity gate that can reproduce the pre-`wlfw_start` ordering
without scan/connect, credentials, DHCP, external ping, or direct eSoC retry.
Only after that static contract is explicit should a bounded live observer be
considered.
