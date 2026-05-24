# Native Init V789 V788 Warning Classifier Report

## Result

- decision: `v789-pm-qos-audio-deferred-probe-boundary-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_v788_warning_classifier_v789.py`
- evidence: `tmp/wifi/v789-v788-warning-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v788_warning_classifier_v789.py
python3 scripts/revalidation/native_wifi_v788_warning_classifier_v789.py plan
python3 scripts/revalidation/native_wifi_v788_warning_classifier_v789.py run
```

## Evidence Summary

| Run | Decision | Warning | Service Notifier | Sysmon | WLFW | `wlan0` |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| V788 | `v788-clean-dsp-lower-readback-blocked` | `5` | `2` | `4` | `0` | `0` |
| V733 | `v733-holder-lower-companion-sysmon-advance` | `0` | `0` | `1` | `0` | `0` |
| V735 | `v735-current-cnss-only-service-publication-advance` | `0` | `1` | `1` | `0` | `0` |
| V787 | `v787-clean-dsp-arm-only-proof-pass` | `0` | `0` | `0` | `0` | `0` |

## Classification

V788 is the only compared run with the warning boundary. The first warning
context shows:

- service-notifier `180` and `74` appear first;
- ADSP/APR audio activity follows;
- `msm_asoc_machine_probe` runs twice;
- the warning is `pm_qos_add_request() called for already added request`;
- the call trace is through `msm_asoc_machine_probe` and
  `deferred_probe_work_func`;
- WLFW, BDF, wiphy, and `wlan0` remain absent.

This does not prove the warning is caused by CNSS itself. It does prove that the
V788 composition crosses a new audio/deferred-probe safety boundary before
Wi-Fi becomes usable. Repeating CNSS-only or widening to HAL/scan/connect is not
justified.

## Safety

V789 was host-only. It executed no device command, reboot, mount, daemon start,
Wi-Fi action, credential use, network change, boot image write, partition write,
or custom kernel flash.

## Next

V790 should be narrower than V788: clean-DSP plus current V401/V490 prep plus
lower-only companion readback, omitting `cnss_diag` and `cnss-daemon`. If that
still triggers the same warning, stop and classify clean-DSP/lower/audio
ordering. If it is warning-free, CNSS-only can be reintroduced later with a more
targeted guard.
