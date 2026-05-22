# Native Init V626 Post-180 Publication Classifier Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_post_180_publication_classifier_v626.py`
- evidence: `tmp/wifi/v626-post-180-publication-classifier/`
- decision: `v626-post-180-service74-publication-gap-classified`

## Scope

V626 is host-only. It compares:

- Android V622:
  `tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/v622-android-mdm-helper-timing-recapture-run/manifest.json`
- native V625:
  `tmp/wifi/v625-fresh-v598-class-live/manifest.json`
  and `tmp/wifi/v625-fresh-v598-class-live/native/dmesg-delta.txt`

No device command, sysfs write, `esoc0` open, daemon start, service-manager
start, Wi-Fi HAL start, scan/connect/link-up, credential use, DHCP, route
change, or external ping was executed.

## Result

```text
decision: v626-post-180-service74-publication-gap-classified
pass: True
reason: V625 reproduces warning-free native service-notifier 180, but Android publishes service 74 6.561ms later and before CNSS userspace netlink while native never publishes 74/WLAN-PD/WLFW service 69.
next: V627 should implement a bounded post-180 service-74/WLAN-PD observer without DSP boot-node writes, service-manager, HAL, scan, connect, credentials, DHCP, routes, or external ping
```

## Evidence Matrix

| subject | classification | evidence | next |
| --- | --- | --- | --- |
| service-notifier `180` | reproduced in native | Android `1`, native `1` | safe partial positive is now reproducible |
| service-notifier `74` | missing in native | Android `1`, native `0`; Android `180->74=6.561ms` | target post-180 service `74` publication |
| WLAN-PD | missing in native | Android `2`, native `0`; Android `180->WLAN-PD=2427.362ms` | keep HAL/connect blocked |
| CNSS timing | not root for service `74` | Android `74` appears before CNSS userspace netlink; native CNSS appears after `180` but no `74` | do not treat CNSS/HAL as next root fix |
| WLFW readback | clean empty | service `69` instances `0/1` both end-of-list, no timeout, no QMI payload | publication absence, not readback transport failure |
| mdm3 state | unresolved | native `mss=ONLINE`, `mdm3=OFFLINING` | keep mdm3/WLAN-PD lower publication as candidate surface |
| safety | clean | native kernel warning `0`; Wi-Fi bring-up `False` | continue bounded observer gates only |

## Timing

Android V622:

```text
service-notifier 180 -> service-notifier 74: 6.561 ms
service-notifier 180 -> wlfw_start:          1415.750 ms
service-notifier 180 -> WLAN-PD:             2427.362 ms
service-notifier 180 -> QMI server:          2429.871 ms
```

Native V625:

```text
service-notifier 180: present
service-notifier 74:  missing
WLAN-PD:              missing
WLFW service 69:      QRTR end-of-list
kernel warning:       0
```

## Interpretation

The active blocker is now after native `service-notifier 180` and before
Android's `service-notifier 74`/WLAN-PD path.

This is below Wi-Fi HAL and below Wi-Fi credentials:

- Android publishes service `74` almost immediately after `180`;
- Android service `74` appears before WLAN-PD, WLFW, QMI server connection, BDF,
  firmware-ready, and `wlan0`;
- native V625 reaches `180` without warnings, but does not publish `74`;
- native WLFW service `69` readback completes with end-of-list, so retrying
  qcwlanstate/HAL would still be premature.

## Next Gate

Proceed to V627 as a bounded live observer:

1. fresh native boot, helper v100, V401, V490, and V625-equivalent preflight;
2. use `subsys_modem` holder plus lower companions only;
3. wait for service-notifier `180`;
4. after `180`, observe for service-notifier `74`, WLAN-PD, and WLFW service
   `69` without direct DSP boot-node writes;
5. keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and
   external ping blocked.
