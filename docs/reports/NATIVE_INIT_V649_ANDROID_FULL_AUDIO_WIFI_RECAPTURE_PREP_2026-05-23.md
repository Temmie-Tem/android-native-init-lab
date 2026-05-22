# Native Init V649 Android Full Audio/Wi-Fi Recapture Prep Report

- date: `2026-05-23 KST`
- status: `preflight-ready`; Wi-Fi external ping is **not** complete
- collector: `scripts/revalidation/native_wifi_android_full_audio_wifi_recapture_v649.py`
- handoff: `scripts/revalidation/android_full_audio_wifi_recapture_handoff_v649.py`

## Result

V649 prep added the Android full audio/Wi-Fi collector and bounded handoff
wrapper. Static validation and plan/dry-run checks passed.

```text
collector plan: v649-android-full-audio-wifi-recapture-plan-ready
handoff plan:   v649-handoff-plan-ready
handoff dryrun: v649-handoff-dryrun-ready
```

The v641 rollback path was explicitly validated in dry-run mode:

```text
--native-image stage3/boot_linux_v641.img
--native-expect-version 'A90 Linux init 0.9.67 (v641)'
```

## Guardrails

The collector is read-only Android ADB evidence collection. It does not enable
Wi-Fi, scan/connect, use credentials, run DHCP, change routes, write sysfs,
start daemons, start HALs, reboot, flash, or ping externally.

The handoff live mode may temporarily write the Android boot image and then
restore native v641. It still does not perform Wi-Fi enable/scan/connect,
credential use, DHCP, route changes, HAL start, daemon start, or external ping.

## Current Device State

Before prep, current native state was v641 with:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok, NCM absent, tcpctl stopped, rshell stopped
```

## Next Gate

Run V649 live handoff to capture Android full audio/Wi-Fi dmesg and return to
native v641. If it captures service `74`/WLAN-PD plus audio context without
duplicate `pm_qos`, move to V650 native ASoC-guarded service `74` retry.
