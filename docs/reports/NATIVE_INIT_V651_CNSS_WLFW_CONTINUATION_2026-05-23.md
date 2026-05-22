# Native Init V651 CNSS/WLFW Continuation Report

- date: `2026-05-23 KST`
- status: `pass`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_cnss_wlfw_continuation_v651.py`
- evidence: `tmp/wifi/v651-cnss-wlfw-continuation/`
- decision: `v651-cnss-daemon-binder-blocks-wlfw-continuation`

## Scope

V651 is host-only. It compares existing Android V649 and native V644 evidence.

No device command, sysfs write, daemon start, service-manager start, Wi-Fi HAL
start, scan/connect/link-up, credential, DHCP, route change, or external ping
was executed.

## Result

```text
decision: v651-cnss-daemon-binder-blocks-wlfw-continuation
pass: True
reason: Android and native both reach CNSS netlink class evidence, but Android treats the genl failure as non-fatal and enters WLFW while native repeats cnss-daemon binder -22 failures and never reaches WLFW/WLAN-PD/QMI/BDF/wlan0.
next: plan V652 bounded service-manager/binder-runtime parity proof around cnss-daemon; keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping blocked
```

## Checks

| check | value |
| --- | --- |
| V650 passed | `True` |
| Android `cnss-daemon` reaches WLFW | `True` |
| Android genl failure is non-fatal | `True` |
| Android reaches WLFW/QMI/BDF | `True` |
| Android binder errors absent | `True` |
| native `cnss-daemon` reaches netlink | `True` |
| native binder errors present | `True` |
| native WLFW absent | `True` |
| native WLFW/QMI/BDF missing | `True` |

## Timing Delta

| source | delta | ms |
| --- | --- | --- |
| Android V649 | service `74` -> `cnss_diag` netlink | `878.778` |
| Android V649 | service `74` -> `cnss-daemon` netlink | `1229.193` |
| Android V649 | `cnss-daemon` netlink -> genl failure | `47.398` |
| Android V649 | genl failure -> `wlfw_start` | `15.312` |
| Android V649 | `wlfw_start` -> WLAN-PD | `1068.607` |
| Android V649 | `wlfw_start` -> QMI server connected | `1071.03` |
| Android V649 | `wlfw_start` -> BDF `regdb.bin` | `1133.179` |
| native V644 | service `74` -> `cnss_diag` netlink | `224.337` |
| native V644 | service `74` -> `cnss-daemon` netlink | `419.975` |
| native V644 | `cnss-daemon` netlink -> binder ioctl `-22` | `51.145` |
| native V644 | binder ioctl `-22` -> binder transaction `-22` | `0.605` |
| native V644 | `cnss-daemon` netlink -> `wlfw_start` | `None` |

## Marker Matrix

| marker | Android V649 | native V644 |
| --- | --- | --- |
| service `74` | `1` | `1` |
| `cnss_diag` netlink | `1` | `1` |
| `cnss-daemon` netlink | `5` | `5` |
| `cnss-daemon` `cld80211` | `0` | `2` |
| genl fail/continue | `1` | `0` |
| `wlfw_start` | `1` | `0` |
| `wlfw_service_request` | `1` | `0` |
| WLAN-PD | `2` | `0` |
| QMI server connected | `1` | `0` |
| BDF `regdb.bin` | `1` | `0` |
| BDF `bdwlan.bin` | `1` | `0` |
| WLAN firmware ready | `1` | `0` |
| `wlan0` | `3` | `0` |
| binder ioctl `-22` | `0` | `1` |
| binder transaction `-22` | `0` | `21` |

## Interpretation

V651 moves the active blocker from the ASoC warning to the
`cnss-daemon` continuation boundary:

```text
Android: service 74 -> CNSS netlink -> non-fatal genl failure -> WLFW -> WLAN-PD/QMI/BDF/wlan0
Native:  service 74 -> CNSS netlink/cld80211 -> binder -22 loop -> no WLFW
```

The next target is not another direct DSP trigger and not Wi-Fi HAL. The next
target is a bounded service-manager/binder-runtime parity proof around
`cnss-daemon`, with success defined as movement to `wlfw_start`/WLFW service
request only.

## Next Gate

V652 should:

1. preserve the current service `74`-positive lower path;
2. add only the minimal binder/service-manager runtime surface needed by
   `cnss-daemon`;
3. collect `cnss-daemon`, binder, WLFW, WLAN-PD, QMI, BDF, and cleanup evidence;
4. keep Wi-Fi HAL, scan/connect, credentials, DHCP, route changes, and external
   ping blocked until WLFW/BDF is present under native init.
