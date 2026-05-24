# Native Init V751 ICNSS Module-init Classifier Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_icnss_module_init_classifier_v751.py`
- plan evidence: `tmp/wifi/v751-icnss-module-init-classifier-plan/`
- run evidence: `tmp/wifi/v751-icnss-module-init-classifier/`
- decision: `v751-boot-wlan-hdd-init-stalls-before-driver-loaded`
- status: `pass`

## Summary

V751 confirms the V750 blocker is not "boot_wlan did nothing." It is narrower:

```text
boot_wlan write entered QCACLD/HDD init
  -> wlan: Loading driver
  -> wlan_hdd_state wlan major(...) initialized
  -> no wlan: driver loaded
  -> no ICNSS-QMI connected
  -> no WLAN FW ready
  -> no wiphy / wlan0
```

Current native still has the ICNSS parent bound, but there is no
`18800000.qcom,icnss/net`, no `18800000.qcom,icnss/ieee80211`, no MHI device,
no wiphy, and no `wlan0`.

## Checks

| check | result |
| --- | --- |
| V750 input | pass; `v750-lower-window-boot-wlan-control-surface-only` |
| boot_wlan entered HDD init | pass |
| driver loaded not reached | pass |
| current link still absent | pass |
| ICNSS parent bound but no netdev | pass |
| Android reference continues | pass; ICNSS-QMI, BDF, firmware-ready, `wlan0` present |

## Key Signals

| signal | value |
| --- | --- |
| V750 `boot_wlan_ok` | `True` |
| V750 `wlan: Loading driver` | `True` |
| V750 `wlan_hdd_state wlan major` | `True` |
| V750 `wlan: driver loaded` | `False` |
| V750 `icnss_qmi: QMI Server Connected` | `False` |
| V750 `WLAN FW is ready` | `False` |
| V750 `Modules not initialized just return` | `30` |
| current ICNSS parent bound | `True` |
| current ICNSS net dir | `False` |
| current ICNSS ieee80211 dir | `False` |
| current MHI devices | `False` |
| current `qcwlanstate` | `OFF` |

## Source Interpretation

The Android QCACLD source maps the observed native markers:

- `boot_wlan` calls `__hdd_module_init` and sets the loader state only after it
  returns success.
- `__hdd_module_init` creates `qcwlanstate`, initializes PLD/HDD, registers the
  WLAN driver, and only then logs driver-loaded state.
- `qcwlanstate` ON waits for `cds_is_driver_loaded`.
- `Modules not initialized just return` corresponds to
  `DRIVER_MODULES_UNINITIALIZED`.

Therefore V750 reached the beginning of static WLAN driver initialization but
did not complete the HDD/PLD/register-driver path. This explains why
`qcwlanstate` stayed `OFF` and link devices never appeared.

## Next Gate

V752 should not repeat standalone `boot_wlan` or `qcwlanstate`. The useful next
gate is one of:

1. bounded CNSS-daemon plus `boot_wlan` ordering proof, still without
   service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
   external ping;
2. deeper read-only/diagnostic instrumentation around HDD/PLD init prerequisites
   if CNSS ordering is judged too broad.

The first candidate is more directly tied to the Android reference because
Android reaches ICNSS-QMI/BDF/firmware-ready, while native now proves it stalls
before that point.

## Source References

- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9406>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9266>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#7947>
