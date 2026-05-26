# V968 Android dmesg eSoC/GPIO Timing

- generated: `2026-05-26`
- scope: host-only classifier over existing Android evidence
- decision: `android-dmesg-needs-magisk-early-sampler`
- pass: `True`
- evidence: `tmp/wifi/v968-android-dmesg-esoc-gpio-timing/manifest.json`

## Summary

V968 classified the existing V913 Android-good boot evidence with focus on MDM3/eSoC GPIO timing.

The important result is split:

- Android-good Wi-Fi ordering is proven from existing dmesg.
- GPIO identity is visible for GPIO135 and GPIO142.
- GPIO level-transition timing is not directly visible in the existing dmesg/sysfs snapshot.

Therefore a Magisk or adb early sampler is justified only if the next native gate requires exact AP2MDM/MDM2AP level-transition timing. It is not required just to continue the Android service-window parity route from V967.

## Key Timeline

| Event | Time |
| --- | ---: |
| `ext-mdm soc:qcom,mdm3` probe | `0.822552s` |
| GPIO135 request | `0.822580s` |
| GPIO142 request | `0.822594s` |
| Wi-Fi HAL legacy start | `6.732796s` |
| Wi-Fi HAL ext start | `6.861900s` |
| `vendor.mdm_helper` start | `8.148170s` |
| `cnss-daemon` start | `8.172571s` |
| `cnss-daemon wlfw_start` | `8.349631s` |
| `/dev/subsys_esoc0` subsystem get | `8.402277s` |
| WLAN-PD indication | `9.414862s` |
| ICNSS QMI connected | `9.417488s` |
| BDF `regdb.bin` | `9.476146s` |
| BDF `bdwlan.bin` | `9.487515s` |
| WLAN FW ready | `14.580127s` |
| `wlan0` event | `14.950217s` |

## Derived Timing

| Interval | Delta |
| --- | ---: |
| `wlfw_start` → `/dev/subsys_esoc0` get | `52.646ms` |
| `wlfw_start` → WLAN-PD indication | `1065.231ms` |
| WLAN-PD indication → ICNSS QMI connected | `2.626ms` |
| `wlfw_start` → WLAN FW ready | `6230.496ms` |
| WLAN FW ready → `wlan0` event | `370.09ms` |

## GPIO Findings

- GPIO135 request is visible at `0.822580s`.
- GPIO142 request is visible at `0.822594s`.
- `/sys/kernel/debug/gpio` snapshot shows GPIO135 and GPIO142 readable after boot.
- `/proc/interrupts` snapshot exposes `msmgpio-dc 142 Edge mdm status`, but the captured count is `0` and the snapshot has no timing dimension.
- Existing evidence does not prove when GPIO135 asserts high, when PMIC GPIO9 deasserts, or when GPIO142 transitions.

## Interpretation

The Android-good path shows `wlfw_start` before `/dev/subsys_esoc0` get, then WLAN-PD, ICNSS QMI, BDF, FW-ready, and `wlan0`. That keeps V967 service-window parity relevant.

The GPIO-level question remains unresolved by existing evidence. A bounded early sampler should be created only if the next native service-window live gate still fails and we need exact AP2MDM/MDM2AP transition timing.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_dmesg_esoc_gpio_timing_v968.py
python3 scripts/revalidation/native_wifi_android_dmesg_esoc_gpio_timing_v968.py
```

Result:

```text
decision: android-dmesg-needs-magisk-early-sampler
pass: True
```

## Next

Proceed to a separate V969 unit:

1. deploy helper `v161` only, or
2. run V967 Android service-window live proof with strict timeout/cleanup.

Do not install a Magisk sampler unless V969 shows that service-window parity is still insufficient and the missing variable is GPIO transition timing.
