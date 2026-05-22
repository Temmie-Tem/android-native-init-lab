# Native Init V648 Audio/ASoC Parity Guard Plan

- date: `2026-05-23 KST`
- cycle: `v648`
- scope: native read-only collector/classifier
- target: determine whether the V644 ASoC/`pm_qos` warning is present at
  current native idle state or only appears when the service `74` path triggers
  ASoC probe

## Background

V647 classified the V644 warning source as `msm_asoc_machine_probe` duplicate
`pm_qos_add_request`, not Wi-Fi HAL or `qcwlanstate`. V648 checks the current
native v641 audio surface without mutating the device and compares it with V644
and Android V622 lower-surface evidence.

## Inputs

- current native v641 via cmdv1 read-only commands;
- V644 warning run:
  `tmp/wifi/v644-live-20260523-071610/native/dmesg-after-companion.txt`
- Android V622 lower-surface reference:
  `tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/v622-android-mdm-helper-timing-recapture-run/android/commands/dmesg-lower-surface-tail.txt`

## Guardrails

V648 may contact the current native device for read-only evidence only. It must
not write sysfs, start daemons, start Wi-Fi HAL, run `qcwlanstate`,
scan/connect, use credentials, run DHCP, change routes, reboot, flash, or ping
externally.

## Success Criteria

V648 passes if it proves:

- current native idle state has no new ASoC probe and no duplicate `pm_qos`
  warning;
- V644 warning appears when the service `74` path starts ASoC probe;
- Android lower-surface evidence is service `74` positive and warning-free;
- Android evidence is recognized as insufficient for full audio boot-order
  parity, so another V644-style retry remains blocked.

## Next Gate

Expected next gate is V649 Android full audio/Wi-Fi dmesg recapture:

- collect full Android early audio + Wi-Fi lower-surface dmesg, not just the
  lower-surface grep tail;
- locate Android ASoC probe, sound-card registration, audio codec registration,
  APR audio channel, service `74`, and WLAN-PD ordering;
- only then design a bounded native retry with an ASoC warning guard.
