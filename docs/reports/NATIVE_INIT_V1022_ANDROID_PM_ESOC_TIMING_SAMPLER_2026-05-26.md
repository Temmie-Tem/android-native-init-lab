# V1022 Android PM/eSoC Timing Sampler

- date: `2026-05-26`
- scope: source/plan validation for Android read-only sampler
- decision: `v1022-android-pm-esoc-timing-plan-ready`
- pass: `True`
- evidence: `tmp/wifi/v1022-android-pm-esoc-timing/manifest.json`

## Summary

V1022 adds a dedicated Android read-only timing sampler for the PM/eSoC reset
handshake gap selected by V1021.

The sampler is designed to run immediately after Android ADB becomes available.
It collects full and focused `dmesg`, repeated process/fd snapshots, service
properties, `/proc/interrupts`, and readable GPIO debug state. It does not start
Wi-Fi components, open eSoC/subsystem control nodes, write sysfs/debugfs/GPIO,
use credentials, or alter routing.

## Why This Route

The Android-good path is already known to reach:

```text
vendor.per_proxy_helper/per_mgr/per_proxy
  -> vendor.mdm_helper
  -> /dev/subsys_esoc0 get
  -> cnss-daemon wlfw_start
  -> WLAN-PD/WLFW/BDF/FW-ready/wlan0
```

V1020 reached the analogous native reset path but blocked in
`sdx50m_toggle_soft_reset`. The missing evidence is timing, not another broad
native retry.

## Captures

| Capture | Purpose |
| --- | --- |
| `props-before` / `props-after` | init service state around the sample window |
| `sample-loop` | repeated `ps -AZ`, focused `/proc/*/fd`, IRQ, and GPIO snapshots |
| `gpio` | GPIO135/GPIO142/PMIC GPIO9 readable surface if available |
| `dmesg-focus` | focused Android boot timeline for PM/eSoC/WLFW markers |
| `dmesg-full` | complete Android kernel log for after-the-fact analysis |

## Guardrails

- ADB shell read-only only
- no native `/dev/subsys_esoc0` retry
- no `/dev/esoc-*` ioctl
- no GPIO/sysfs/debugfs write
- no service-manager or Wi-Fi HAL start
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no boot image or partition write

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py
python3 scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py plan
```

Result:

```text
decision: v1022-android-pm-esoc-timing-plan-ready
pass: True
next: boot Android and run V1022 during the early PM/eSoC window
```

## Next

Run V1022 during the next Android boot as early as possible:

```bash
python3 scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py run
```

If the one-shot `vendor.per_proxy_helper` fd window is missed again, the next
unit should integrate V1022 into an Android handoff wrapper that starts before
`wait-boot-complete`, or use a small Magisk/post-fs-data read-only sampler.

