# Native Init V647 Warning Source Classifier Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_warning_source_classifier_v647.py`
- evidence: `tmp/wifi/v647-warning-source-classifier/`
- decision: `v647-audio-asoc-pm-qos-warning-source-classified`

## Scope

V647 is host-only. It compares V619, V638, V644, and Android V622/V628
evidence. It does not contact the device, write sysfs, start daemons, start
Wi-Fi HAL, run `qcwlanstate`, scan/connect, use credentials, run DHCP, change
routes, reboot, flash, or ping externally.

## Result

```text
decision: v647-audio-asoc-pm-qos-warning-source-classified
pass: True
reason: V644 warning call trace is msm_asoc_machine_probe/pm_qos; V619/V638 reproduce the same warning without service74, while Android has service74 without kernel_warning
next: plan V648 audio/ASoC parity guard before any V644-style live retry or Wi-Fi HAL/qcwlanstate
```

## Case Matrix

| case | service `74` | ASoC probe | duplicate `pm_qos` | QoS warning | audio signature |
| --- | ---: | ---: | ---: | ---: | --- |
| V619 direct all-sibling Android-order replay | `0` | `22` | `21` | `21` | yes |
| V638 firmware all-sibling composite | `0` | `14` | `13` | `13` | yes |
| V644 clean-DSP CNSS service `74` run | `1` | `2` | `1` | `1` | yes |
| Android V622 post-`74` reference | `1` | not classified | not classified | `0` | warning-free reference |

## V644 Warning Context

V644 warning context is audio/ASoC-specific:

```text
sm8150-asoc-snd ... msm_asoc_machine_probe: pm noise
sm8150-asoc-snd ... ASoC: platform /soc/qcom,msm-pcm-voice not registered
msm_asoc_machine_probe: Enter
sm8150-asoc-snd ... msm_asoc_machine_probe: pm noise
pm_qos_add_request() called for already added request
WARNING: CPU ... at kernel/power/qos.c:616 pm_qos_add_request
```

## Interpretation

The V644 warning is not in Wi-Fi HAL, `qcwlanstate`, WLFW, BDF, or
`icnss_qmi`. It is in `msm_asoc_machine_probe` and duplicate
`pm_qos_add_request`.

Service `74` is a close temporal neighbor in V644, but it is not a unique root
cause. V619 and V638 reproduce the same warning class without service `74`.
Android V622 reaches service `74` without a kernel warning.

## Next Gate

Proceed to V648 as an audio/ASoC parity guard:

1. compare Android and native ASoC/audio probe state around lower Wi-Fi
   readiness;
2. identify the missing Android-like platform-registration or ordering guard;
3. keep V644 live retry, Wi-Fi HAL, `qcwlanstate`, scan/connect, DHCP, route
   changes, and external ping blocked until the ASoC warning gate is clean.
