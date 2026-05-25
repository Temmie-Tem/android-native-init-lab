# Native Init V913 Android eSoC GPIO Timeline Tool Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| tool static validation | `scripts/revalidation/native_wifi_android_esoc_gpio_timeline_v913.py` | `py_compile pass` |
| plan mode | `tmp/wifi/v913-android-esoc-gpio-timeline-plan/manifest.json` | `v913-android-esoc-gpio-timeline-plan-ready` |
| current-state preflight | `tmp/wifi/v913-android-esoc-gpio-timeline-preflight/manifest.json` | `v913-android-adb-unavailable` |

V913 now has a bounded Android read-only capture tool. The current device state
is native init, so Android ADB is not available and the actual Android timeline
capture has not run yet.

## Implementation

- Added `scripts/revalidation/native_wifi_android_esoc_gpio_timeline_v913.py`.
- Captures Android ADB read-only surfaces only:
  - `dmesg`;
  - focused dmesg;
  - `/proc/interrupts`;
  - `subsys9` / eSoC state surfaces;
  - GPIO/debugfs GPIO read surface if readable;
  - bounded process/fd summaries for `mdm_helper`, `ks`, and related actors.
- Classifies timeline markers for GPIO135/AP2MDM, PMIC GPIO9/reset hints,
  GPIO142/MDM2AP, PCIe/MHI, `mdm3=ONLINE`, `ks`, MHI pipe, WLAN-PD, WLFW, BDF,
  and `wlan0`.

## Current-State Preflight

The host ADB server is reachable, but no Android device is listed:

```text
List of devices attached
```

This matches the current native-init state observed through the serial bridge.
No Android shell command, eSoC ioctl, subsystem trigger, Wi-Fi HAL, scan/connect,
DHCP/route, credential use, external ping, boot image write, or partition write
occurred.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_esoc_gpio_timeline_v913.py
python3 scripts/revalidation/native_wifi_android_esoc_gpio_timeline_v913.py \
  --out-dir tmp/wifi/v913-android-esoc-gpio-timeline-plan \
  plan
python3 scripts/revalidation/native_wifi_android_esoc_gpio_timeline_v913.py \
  --out-dir tmp/wifi/v913-android-esoc-gpio-timeline-preflight \
  preflight
```

Guardrails from both manifests report:

- `native_subsys_trigger_executed=false`
- `esoc_ioctl_executed=false`
- `gpio_write_executed=false`
- `sysfs_write_executed=false`
- `debugfs_write_executed=false`
- `wifi_hal_start_executed=false`
- `scan_connect_linkup=false`
- `credentials_used=false`
- `dhcp_routing=false`
- `external_ping=false`

## Next

Boot Android, then run:

```bash
python3 scripts/revalidation/native_wifi_android_esoc_gpio_timeline_v913.py run
```

If V913 proves the positive Android GPIO/eSoC order, proceed to V914
source/build-only helper support for
`wifi-companion-mdm-helper-runtime-subsys-trigger-capture`. If it does not,
adjust the native trigger model before any `/dev/subsys_esoc0` live trigger.
