# Native Init V783 Android/Native PIL Gap Plan

## Goal

Classify the post-V782 gap without device interaction. V782 proved that stock
v724 can count real `msm_pil_event:pil_notif` events during the lower-window
transition, but still stopped before service-notifier, WLAN-PD, WLFW, BDF,
wiphy, and `wlan0`.

## Scope

- Host-only analysis over existing evidence.
- Android/native marker comparison for the lower modem/WLAN chain.
- Selection of the next safe work unit before any further live trigger.

## Inputs

- `tmp/wifi/v519-android-native-qrtr-modem-delta/inputs/android-dmesg-wifi-cnss-tail.txt`
- `tmp/wifi/v649-android-full-audio-wifi-handoff-live-20260523-074556/v649-android-full-audio-wifi-recapture-run/android/commands/dmesg-audio-wifi-tail.txt`
- `tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/v611-android-lower-surface-recapture-run/android-lower-surface-state.txt`
- `tmp/wifi/v782-bpf-counter-boot-wlan/manifest.json`
- `tmp/wifi/v782-bpf-counter-boot-wlan/native/dmesg-delta.txt`
- `tmp/wifi/v782-bpf-counter-boot-wlan/native/bpf-counter-collect.txt`

## Method

1. Read only exact evidence paths with bounded file-size limits.
2. Parse QRTR, sysmon, service-notifier, WLAN-PD, ICNSS-QMI, BDF,
   firmware-ready, `wlan0`, memshare, and CMA markers.
3. Compare Android marker order and deltas against native V782.
4. Preserve BPF count metadata and note that V782 did not capture tracepoint
   payload fields.
5. Emit a next-step classifier without boot image write, reboot, device command,
   Wi-Fi HAL start, scan/connect, DHCP, route change, or external ping.

## Success Criteria

- Required evidence files are present.
- Runner passes with `device_commands_executed=false`.
- Android reference reaches service-notifier `74/180`, WLAN-PD, ICNSS-QMI,
  BDF, firmware-ready, and `wlan0`.
- Native V782 gap is classified against that reference.
- Next candidate is narrowed to read-only evidence, not another blind
  `boot_wlan` or daemon-ordering retry.

## Safety Boundaries

- no serial bridge/device command execution
- no boot image or partition write
- no reboot
- no Wi-Fi HAL/service-manager start
- no Wi-Fi scan/connect or credential use
- no DHCP, route changes, or external ping
- no `qcwlanstate ON`
- no module load/unload, bind/unbind, or `esoc0` access

## Runner

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_native_pil_gap_v783.py
python3 scripts/revalidation/native_wifi_android_native_pil_gap_v783.py plan
python3 scripts/revalidation/native_wifi_android_native_pil_gap_v783.py run
```
