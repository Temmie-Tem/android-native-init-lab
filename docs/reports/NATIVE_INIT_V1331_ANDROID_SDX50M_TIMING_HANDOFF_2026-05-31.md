# Native Init V1331 Android SDX50M Timing Handoff

## Summary

- Cycle: `V1331`
- Type: bounded Android handoff + read-only collector
- Handoff decision: `v1331-android-wlfw-before-subsys-esoc0`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1331-android-sdx50m-timing-handoff/manifest.json`
  - `tmp/wifi/v1331-android-sdx50m-timing-handoff/summary.md`
  - `tmp/wifi/v1331-android-sdx50m-timing-handoff/v1331-android-sdx50m-timing-recapture-run/manifest.json`
  - `tmp/wifi/v1331-android-sdx50m-timing-handoff/v1331-android-sdx50m-timing-recapture-run/summary.md`
- Scripts:
  - `scripts/revalidation/android_sdx50m_timing_handoff_v1331.py`
  - `scripts/revalidation/native_wifi_android_sdx50m_timing_recapture_v1331.py`

V1331 implemented the V1330 plan by extending the Android handoff pattern and
adding a read-only collector for Android `getprop`, dmesg monotonic markers,
process/fd snapshots, and interrupt lines. The handoff temporarily booted the
known Android boot image, collected evidence, rebooted to recovery, restored
`stage3/boot_linux_v724.img`, and verified native init after rollback.

## Result

The live collector captured an Android-positive Wi-Fi lower chain:

| marker | first timestamp |
|---|---:|
| `wlfw_start` | `8.396410s` |
| `__subsystem_get(esoc0)` | `8.449943s` |
| `BDF regdb.bin` | `9.513055s` |
| `wlan0` | `14.772258s` |

The collector did not capture PCIe RC1/L0 or MHI pipe dmesg markers in this
run. The corrected live decision is therefore based on the markers that were
captured on one dmesg monotonic clock: Android shows a WLFW userspace marker
before the captured `subsys_get(esoc0)` marker, followed by BDF download and
`wlan0`. That means the next useful classifier should focus on earlier Android
`cnss-daemon`/`per_mgr`/provider ordering, not on a longer native wait after
`mdm_subsys_powerup`.

## Rollback Verification

- Native version after rollback: `A90 Linux init 0.9.68 (v724)`
- Post-run selftest: `pass=11 warn=1 fail=0`
- Handoff safety booleans: Wi-Fi bring-up `false`, external ping `false`

## Safety

No Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping,
native PMIC/GPIO/GDSC/eSoC write, direct eSoC ioctl/notify, blind `BOOT_DONE`,
or partition write occurred outside the bounded Android handoff/rollback path.

## Next

V1332 should be host-only first: classify the V1331 Android evidence against
V1328 native timing and answer whether native is missing an earlier
`cnss-daemon` WLFW request/provider state before `pm-service` enters
`mdm_subsys_powerup`.
