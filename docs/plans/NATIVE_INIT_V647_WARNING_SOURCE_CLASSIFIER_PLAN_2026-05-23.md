# Native Init V647 Warning Source Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v647`
- scope: host-only classifier
- target: classify the `pm_qos_add_request` warning source seen immediately
  after V644 service `74`

## Background

V644 reached native service `180/74`, but hit a kernel warning about
`11.789 ms` after service `74`. V645 showed service `180` alone is
warning-free. V646 showed Android normally waits about `2.421 s` from service
`74` to WLAN-PD, so the V644 warning is not a "wait longer" problem.

## Inputs

- V619 warning-positive direct all-sibling replay:
  `tmp/wifi/v619-android-order-post-sysmon-observer-run/native/dmesg-delta.txt`
- V638 warning-positive firmware all-sibling composite:
  `tmp/wifi/v638-firmware-sibling-live-20260523-060104/native/dmesg-after-sibling.txt`
- V644 warning-positive clean-DSP service `74` run:
  `tmp/wifi/v644-live-20260523-071610/manifest.json`
- V628 Android V622 post-service `74` timing reference:
  `tmp/wifi/v628-service74-publisher-classifier/manifest.json`

## Guardrails

V647 is host-only and must not contact the device, write sysfs, start daemons,
start Wi-Fi HAL, run `qcwlanstate`, scan/connect, use credentials, run DHCP,
change routes, reboot, flash, or ping externally.

## Success Criteria

V647 passes if it proves:

- V644 warning context includes `msm_asoc_machine_probe` and duplicate
  `pm_qos_add_request`;
- V619/V638 reproduce the same ASoC/`pm_qos` warning class without service
  `74`;
- Android V622 reaches service `74` with no kernel warning;
- next live work remains blocked until an audio/ASoC parity guard is defined.

## Next Gate

Expected next gate is V648 audio/ASoC parity guard:

- compare Android and native audio/ASoC probe state around the Wi-Fi lower path;
- identify the missing Android-like ordering or platform-registration condition;
- only then design a bounded live retry that keeps HAL, scan/connect, DHCP,
  route changes, and external ping blocked until the warning gate is clean.
