# Native Init V645 V644 Warning Attribution Plan

- date: `2026-05-23 KST`
- cycle: `v645`
- scope: host-only classifier
- target: classify the V644 `pm_qos_add_request` warning around service `74`
  before any live retry or HAL/qcwlanstate attempt

## Background

V644 reached service-notifier `180` and `74` for the first time in the native
clean-DSP branch, then immediately hit a `pm_qos_add_request` warning. Since
the run did not write DSP boot nodes in the live phase, the warning needs a new
attribution pass before moving toward HAL or connect tests.

## Inputs

- V619 warning/no-service74 path:
  `tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json`
- V627 service180-only/no-warning path:
  `tmp/wifi/v627-post-180-observer-live-v2/manifest.json`
- V642 clean-DSP/no-CNSS/no-warning path:
  `tmp/wifi/v642-live-20260523-070145/manifest.json`
- V644 service74/warning path:
  `tmp/wifi/v644-live-20260523-071610/manifest.json`

## Guardrails

V645 is host-only and must not:

- contact the device;
- write sysfs or mount anything;
- start companion daemons, CNSS, service-manager, Wi-Fi HAL, `wificond`,
  supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Checks

1. Compare service `180`, service `74`, WLAN-PD, QMI, and kernel-warning
   counts across V619/V627/V642/V644.
2. Compute V644 service `74` to warning timing.
3. Verify clean-DSP/no-CNSS V642 is warning-free.
4. Verify service `180`-only V627 is warning-free.
5. Preserve V619 as a separate warning class showing warning can occur without
   service `74` when direct DSP/sibling paths are involved.

## Success Criteria

V645 passes if it selects a conservative next gate without executing live
actions:

- warning is not caused by clean-DSP state alone;
- warning is not caused by service `180` alone;
- V644 service `74` publication and warning are tightly coupled in time;
- V619 shows there may be a shared DSP/audio deferred-probe warning class;
- HAL/qcwlanstate/scan/connect remain blocked.

## Next Gate

Expected next gate is V646 host-only Android post-service74 timing comparison:

- compare Android service `74` to WLAN-PD/WLFW timing against V644;
- identify whether Android has a warning-free delay, ACK, or extra publisher
  between service `74` and WLAN-PD;
- only then decide whether any bounded live retry is justified.
