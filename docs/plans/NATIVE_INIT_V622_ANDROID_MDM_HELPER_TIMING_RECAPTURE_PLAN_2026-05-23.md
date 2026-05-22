# Native Init V622 Android MDM Helper Timing Recapture Plan

- date: `2026-05-23 KST`
- cycle: `v622`
- scope: Android same-boot read-only recapture plus guarded handoff
- target: close V621's cross-boot timing gap for `vendor.mdm_launcher`,
  `vendor.mdm_helper`, and first lower QMI/service-notifier markers

## Background

V621 classified `vendor.mdm_helper` as the real Android service candidate and
`vendor.mdm_launcher` as a `ro.baseband`-gated oneshot wrapper. The remaining
gap is that the available `mdm_helper` boottime and service-notifier dmesg came
from different Android captures.

V622 captures both evidence classes from the same Android boot. The result is
used only to decide whether a later native start-only proof is justified.

## Guardrails

V622 must not:

- enable/disable Wi-Fi, scan, connect, link up, use credentials, DHCP, routes,
  or external ping;
- start CNSS, service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd, or
  native companion daemons;
- write sysfs, `boot_wlan`, `qcwlanstate`, DSP boot nodes, rfkill, modules, or
  properties;
- send QRTR/QMI payloads.

The handoff wrapper may temporarily flash Android boot and restore native boot
only when explicit/bypass approval flags are present. The collector itself is
read-only.

## Implementation

- `scripts/revalidation/native_wifi_android_mdm_helper_timing_recapture_v622.py`
  - Android ADB collector with `plan`, `preflight`, and `run` modes.
  - Captures targeted properties:
    `ro.boottime.vendor.mdm_launcher`,
    `ro.boottime.vendor.mdm_helper`, companion boottimes, CNSS boottimes, and
    related `init.svc.*` state.
  - Captures same-boot dmesg markers for `sysmon-qmi`,
    `service-notifier 180/74`, WLAN-PD, WLFW/BDF, and `wlan0`.
- `scripts/revalidation/android_mdm_helper_timing_handoff_v622.py`
  - Reuses the existing Android boot handoff and native rollback primitives.
  - Waits for `sys.boot_completed=1`, settles briefly, runs the V622 collector,
    then restores native init.

## Success Criteria

V622 passes if it selects one of these outcomes:

- `v622-mdm-helper-pre-notifier-candidate`
- `v622-mdm-launcher-window-not-helper-classified`
- `v622-mdm-helper-post-notifier-not-root-trigger`

If Android ADB or dmesg/property evidence is missing, V622 fails closed with an
evidence-gap decision. Passing V622 does not authorize CNSS/HAL, Wi-Fi scan,
connect, or external ping.
