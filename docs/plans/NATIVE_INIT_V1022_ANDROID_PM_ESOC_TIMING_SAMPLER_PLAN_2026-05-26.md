# V1022 Android PM/eSoC Timing Sampler Plan

- date: `2026-05-26`
- type: Android read-only sampler
- selected after: V1021 reset-handshake classifier

## Objective

Capture Android-good PeripheralManager/eSoC timing before another native
`/dev/subsys_esoc0` retry.

V1020 proved that native can reach the SDX50M reset path, but the child blocks
inside `sdx50m_toggle_soft_reset`. V1021 selected Android read-only recapture
because the existing Android evidence proves a working WLFW chain but does not
pin down the early `vendor.per_proxy_helper` fd window, GPIO135/AP2MDM timing,
GPIO142/MDM2AP IRQ timing, or PMIC GPIO9 soft-reset timing.

## Approach

Use normal Android boot plus early ADB collection. A Magisk module is not the
first choice because full boot `dmesg` already preserves the early eSoC/GPIO
sequence, and an ADB sampler avoids adding boot-time module latency.

The sampler records:

- init service state for `vendor.per_proxy_helper`, `vendor.per_mgr`,
  `vendor.per_proxy`, `vendor.mdm_helper`, `cnss-daemon`, and Wi-Fi actors
- repeated focused `ps -AZ` and `/proc/*/fd` snapshots
- `/proc/interrupts` samples for `mdm status`/GPIO142 style IRQ lines
- `/sys/kernel/debug/gpio` focus lines if Android exposes them as readable
- full Android `dmesg`
- focused Android `dmesg` lines for `mdm`, `esoc`, `gpio`, `ap2mdm`,
  `mdm2ap`, `pmic`, `pm8150`, ICNSS/CNSS, WLFW, BDF, and `wlan0`

## Commands

Plan-only validation:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py
python3 scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py plan
```

Live Android capture, to run as soon as ADB sees Android:

```bash
python3 scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py run
```

If multiple Android devices are visible:

```bash
python3 scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py --serial <adb-serial> run
```

## Hard Gates

- Android ADB shell read-only only
- no native `/dev/subsys_esoc0` open
- no `/dev/esoc-*` ioctl
- no eSoC notify, image response, or BOOT_DONE
- no GPIO/sysfs/debugfs write
- no service-manager start
- no Wi-Fi HAL start
- no scan/connect/link-up
- no credentials
- no DHCP, route, or external ping
- no boot image or partition write

## Success Criteria

The sampler must produce a private evidence directory and one of these decisions:

- `v1022-android-pm-esoc-fd-timing-captured`
- `v1022-android-pm-esoc-timing-captured-fd-window-missed`
- `v1022-android-pm-esoc-timing-incomplete`
- `v1022-android-adb-unavailable`

Capturing WLFW continuation with a missed `per_proxy_helper` fd window is still a
valid result; it means the next unit should integrate this sampler into an
Android handoff flow that starts before `wait-boot-complete`, or use a small
Magisk/post-fs-data read-only sampler if ADB cannot arrive early enough.

## Evidence

- default run directory: `tmp/wifi/v1022-android-pm-esoc-timing`
- latest pointer: `tmp/wifi/latest-v1022-android-pm-esoc-timing.txt`

