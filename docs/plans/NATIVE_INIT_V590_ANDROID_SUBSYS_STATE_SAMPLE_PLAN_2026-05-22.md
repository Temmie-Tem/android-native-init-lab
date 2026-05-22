# Native Init V590 Android Subsystem State Sample Plan

- date: `2026-05-22 KST`
- objective: collect a read-only Android-side modem/esoc subsystem state sample to resolve the V589 evidence gap
- status: `planned`

## Context

V589 proved that Android reaches the QRTR/sysmon/service-notifier/WLAN-PD readiness timeline, while V588 native companion-window evidence shows `modem` and `esoc0` stuck in `OFFLINING`. The missing item is a direct Android sysfs state sample for those same subsystem nodes.

## Gate

- Gate: Android read-only sample.
- Runner: `scripts/revalidation/native_wifi_android_subsys_state_sample_v590.py`.
- Expected normalized output: `tmp/wifi/v590-android-subsys-state-sample/android-subsys-state.txt`.

## Guardrails

- Android ADB only; no native daemon replay.
- No boot image flash from this collector.
- No reboot or recovery handoff from this collector.
- No daemon start.
- No subsystem sysfs write.
- No qcwlanstate/sysfs driver-state write.
- No Wi-Fi enable command.
- No Wi-Fi HAL start.
- No supplicant/hostapd/wificond start.
- No scan/connect/link-up/DHCP/routing.
- No external ping.
- No credential use or credential-bearing evidence.

## Implementation

1. Add an ADB-based collector with `plan`, `preflight`, and `run`.
2. If Android ADB is unavailable, classify as `v590-android-adb-unavailable` without failing the loop.
3. If Android ADB is available, run read-only `su -c` commands only:
   - boot-complete and selected service properties,
   - modem/esoc subsystem values,
   - delayed modem/esoc subsystem values,
   - `/sys/bus/rpmsg/devices`,
   - `/proc/net/qrtr`,
   - readiness-related dmesg tail.
4. Write a normalized `android-subsys-state.txt` sample.
5. Classify whether Android state is non-offline, still offline-class, missing, or not boot-complete.

## Success Criteria

V590 passes if it either:

- captures direct Android modem/esoc values, or
- proves Android ADB is not currently available and leaves a safe next action.

It must not start Wi-Fi, scan, connect, route, ping, or store credentials.

## Expected Decision In Current Native State

Likely decision before Android handoff: `v590-android-adb-unavailable`.

After Android boot: likely useful decisions are:

- `v590-android-subsys-nonoffline-captured`, if Android has non-offline subsystem state, or
- `v590-android-subsys-still-offline-captured`, if Android is also offline-class at the sample time.

## Next Gate After V590

If V590 captures non-offline Android subsystem state, rerun the V589 comparator with the V590 normalized state sample and then plan the smallest safe native subsystem readiness trigger. If V590 only shows offline-class Android state, collect a tighter boot-time window before designing a native trigger.
