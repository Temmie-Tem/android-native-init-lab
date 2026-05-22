# Native Init V648 Audio/ASoC Parity Guard Live Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_audio_asoc_parity_guard_v648.py`
- evidence: `tmp/wifi/v648-audio-asoc-parity-guard/`
- decision: `v648-current-clean-v644-asoc-gap-classified`

## Scope

V648 contacted the current native v641 device for read-only evidence only. It
did not write sysfs, start daemons, start Wi-Fi HAL, run `qcwlanstate`,
scan/connect, use credentials, run DHCP, change routes, reboot, flash, or ping
externally.

## Result

```text
decision: v648-current-clean-v644-asoc-gap-classified
pass: True
reason: current native v641 is warning-free and has not started ASoC probe; V644 warning appears only when ASoC probe starts during the service74 path; Android lower evidence is warning-free but lacks full early audio context
next: plan V649 Android full audio/Wi-Fi dmesg recapture before any V644-style retry
```

## Case Matrix

| case | service `74` | ASoC probe | duplicate `pm_qos` | audio locator down | warning dirty |
| --- | ---: | ---: | ---: | ---: | --- |
| current native v641 | `0` | `0` | `0` | `1` | no |
| V644 service `74` path | `1` | `2` | `1` | `0` | yes |
| Android V622 lower reference | `1` | `0` | `0` | `0` | no |

## Interpretation

Current native v641 is clean at idle: the collected audio dmesg tail has no
ASoC probe and no duplicate `pm_qos` warning. V644 starts ASoC probe during the
service `74` path and immediately hits duplicate `pm_qos`.

Android V622 lower-surface evidence reaches service `74` without a kernel
warning, but it is not a full early audio boot trace. It proves Android can be
service `74` positive and warning-free; it does not yet prove the exact ASoC
ordering that prevents the duplicate `pm_qos` warning.

## Next Gate

Proceed to V649 as Android full audio/Wi-Fi dmesg recapture:

1. collect Android early audio + Wi-Fi lower-surface dmesg with ASoC/APR/audio
   markers included;
2. compare Android ASoC probe/sound-card/audio-codec timing against V644;
3. keep V644 live retry, Wi-Fi HAL, `qcwlanstate`, scan/connect, DHCP, route
   changes, and external ping blocked until the ASoC warning guard is clean.
