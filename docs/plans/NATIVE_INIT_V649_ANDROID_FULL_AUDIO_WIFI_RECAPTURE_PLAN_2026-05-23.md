# Native Init V649 Android Full Audio/Wi-Fi Recapture Plan

- date: `2026-05-23 KST`
- cycle: `v649`
- scope: Android read-only recapture plus bounded native rollback handoff
- target: capture a full Android same-boot audio/ASoC + Wi-Fi lower-surface
  reference before any V644-style native retry

## Background

V648 proved current native v641 idle is warning-free and that the V644 warning
appears when the service `74` path starts ASoC probe. Existing Android V622
evidence is service `74`/WLAN-PD positive and warning-free, but its dmesg grep
was focused on lower Wi-Fi readiness and does not fully capture early
audio/ASoC ordering.

## Implementation

- Collector:
  `scripts/revalidation/native_wifi_android_full_audio_wifi_recapture_v649.py`
- Handoff:
  `scripts/revalidation/android_full_audio_wifi_recapture_handoff_v649.py`

The collector captures:

- Android boot/service properties;
- full audio + lower Wi-Fi dmesg markers;
- unfiltered dmesg tail;
- `/proc/asound/cards`, `/dev/snd`, and platform audio device names.

The handoff temporarily boots Android, waits for `sys.boot_completed=1`, runs
the V649 collector, then restores native v641 using
`stage3/boot_linux_v641.img`.

## Guardrails

V649 must not enable Wi-Fi, scan/connect, use credentials, run DHCP, change
routes, start Wi-Fi HALs, start native daemons, write sysfs, reboot except
inside the bounded Android/native rollback handoff, or ping externally.

## Success Criteria

V649 passes if Android same-boot evidence proves:

- service `74` and WLAN-PD are present;
- audio/ASoC context is present;
- duplicate `pm_qos_add_request` and `kernel/power/qos.c:616` warning are
  absent;
- native rollback returns to v641 with selftest clean.

## Prepared Commands

Plan/dry-run validation:

```text
python3 scripts/revalidation/native_wifi_android_full_audio_wifi_recapture_v649.py --out-dir tmp/wifi/v649-collector-plan plan
python3 scripts/revalidation/android_full_audio_wifi_recapture_handoff_v649.py --out-dir tmp/wifi/v649-handoff-dry-run-v641 --native-image stage3/boot_linux_v641.img --native-expect-version 'A90 Linux init 0.9.67 (v641)' dry-run
```

Live handoff, when proceeding:

```text
python3 scripts/revalidation/android_full_audio_wifi_recapture_handoff_v649.py \
  --out-dir tmp/wifi/v649-android-full-audio-wifi-handoff-live-<ts> \
  --native-image stage3/boot_linux_v641.img \
  --native-expect-version 'A90 Linux init 0.9.67 (v641)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
```

## Next Gate

If V649 captures an Android warning-free audio/Wi-Fi reference, proceed to V650:
native ASoC-guarded clean-DSP service `74` retry with HAL, scan/connect, DHCP,
route changes, credentials, and external ping still blocked.
