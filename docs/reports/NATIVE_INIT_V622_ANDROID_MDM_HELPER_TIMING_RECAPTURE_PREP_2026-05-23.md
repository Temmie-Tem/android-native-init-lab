# Native Init V622 Android MDM Helper Timing Recapture Prep Report

- date: `2026-05-23 KST`
- status: `prep-ready`; live Android handoff not executed in this prep report
- collector: `scripts/revalidation/native_wifi_android_mdm_helper_timing_recapture_v622.py`
- handoff: `scripts/revalidation/android_mdm_helper_timing_handoff_v622.py`
- plan evidence: `tmp/wifi/v622-android-mdm-helper-timing-handoff-plan/`
- dry-run evidence: `tmp/wifi/v622-android-mdm-helper-timing-handoff-dryrun/`

## Scope

V622 adds a same-boot Android read-only collector and a guarded handoff wrapper
to close the V621 cross-boot timing gap.

The prep validation did not reboot, enter recovery, write boot, start daemons,
start service-manager, start Wi-Fi HAL, scan/connect/link-up, use credentials,
run DHCP, change routes, or ping externally.

## Validation

```text
python3 -m py_compile scripts/revalidation/native_wifi_android_mdm_helper_timing_recapture_v622.py scripts/revalidation/android_mdm_helper_timing_handoff_v622.py
python3 scripts/revalidation/native_wifi_android_mdm_helper_timing_recapture_v622.py --out-dir tmp/wifi/v622-android-mdm-helper-timing-recapture-plan plan
python3 scripts/revalidation/android_mdm_helper_timing_handoff_v622.py --out-dir tmp/wifi/v622-android-mdm-helper-timing-handoff-plan plan
python3 scripts/revalidation/android_mdm_helper_timing_handoff_v622.py --out-dir tmp/wifi/v622-android-mdm-helper-timing-handoff-dryrun dry-run
python3 scripts/revalidation/native_wifi_android_mdm_helper_timing_recapture_v622.py --out-dir tmp/wifi/v622-android-mdm-helper-timing-recapture-preflight preflight
```

## Results

| check | decision | pass | meaning |
| --- | --- | --- | --- |
| collector plan | `v622-android-mdm-helper-timing-plan-ready` | true | no ADB command executed |
| handoff plan | `v622-handoff-plan-ready` | true | execution plan generated without mutation |
| handoff dry-run | `v622-handoff-dryrun-ready` | true | all steps recorded without mutation |
| collector preflight in native state | `v622-android-adb-unavailable` | false | expected: current device is native init, so Android handoff is required |

## Next Gate

Run the V622 handoff live with rollback flags. The expected live output should
classify whether `vendor.mdm_helper` starts before first service-notifier,
whether only the launcher window precedes it, or whether both are later than
the lower QMI publication marker.

CNSS, service-manager, Wi-Fi HAL, scan/connect/link-up, credentials, DHCP,
route changes, and external ping remain blocked until V622 explains the lower
timing order.
