# Native Init V646 Android Post-Service74 Timing Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_android_post74_timing_v646.py`
- evidence: `tmp/wifi/v646-android-post74-timing/`
- decision: `v646-native-warning-preempts-android-post74-window`

## Scope

V646 is host-only. It compares Android V622 timing from the V628 classifier with
native V644 timing. It does not contact the device, start daemons, start Wi-Fi
HAL, scan/connect, use credentials, run DHCP, change routes, or ping
externally.

## Result

```text
decision: v646-native-warning-preempts-android-post74-window
pass: True
reason: Android waits 2420.801ms from service74 to WLAN-PD, but V644 warns after 11.789ms
next: plan V647 warning-source classifier; do not repeat V644 or start HAL/qcwlanstate
```

## Timing

| item | ms |
| --- | ---: |
| Android service `180` → service `74` | `6.561` |
| Android service `74` → WLFW start | `1409.189` |
| Android service `74` → WLAN-PD | `2420.801` |
| Android service `74` → QMI server connected | `2423.31` |
| V644 service `74` → warning | `11.789` |
| V644 service `74` → WLAN-PD | missing |
| V644 service `74` → QMI server connected | missing |

## Interpretation

Android does not immediately proceed from service `74` to WLAN-PD. There is a
multi-second post-`74` window before WLFW/WLAN-PD/QMI readiness:

```text
service 74
  -> ~1.409 s -> WLFW start
  -> ~2.421 s -> WLAN-PD
  -> ~2.423 s -> QMI server connected
```

V644 instead hits `pm_qos_add_request` warning about `11.789 ms` after service
`74`. That is too early to be treated as "wait longer for WLAN-PD." The warning
preempts the normal Android post-`74` path.

## Next Gate

Proceed to V647 warning-source classifier:

1. inspect V644 and V619 warning call traces;
2. compare against Android's warning-free post-`74` window;
3. classify whether the warning is tied to audio deferred probe, CNSS child
   timing, service `74` callback, missing Android delay/ACK context, or another
   DSP/audio dependency;
4. keep V644 live retry, HAL, `qcwlanstate`, scan/connect, credentials, DHCP,
   routes, and external ping blocked.
